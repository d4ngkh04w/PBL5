import os
from abc import ABC, abstractmethod

import torch
import torch.nn as nn
from torchvision import models
from PIL import Image

CLASS_NAMES = [
    "battery",
    "biological",
    "cardboard",
    "clothes",
    "e-waste",
    "glass",
    "metal",
    "paper",
    "plastic",
    "shoes",
]

MAPPED_CLASS_NAMES = {
    "battery": "hazardous",
    "biological": "organic",
    "cardboard": "recycling",
    "clothes": "non_recyclable",
    "e-waste": "hazardous",
    "glass": "recycling",
    "metal": "recycling",
    "paper": "recycling",
    "plastic": "recycling",
    "shoes": "non_recyclable",
}


class Model(ABC):
    """
    Abstract base class cho tất cả classification models
    """

    def __init__(
        self,
        model_path: str,
        class_names: list[str],
        mapped_class_names: dict[str, str],
        device: torch.device | None = None,
    ) -> None:
        self.model_path = os.path.abspath(model_path)
        self.class_names = class_names
        self.mapped_class_names = mapped_class_names
        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found at {self.model_path}")

        self.net: nn.Module = self._build_architecture()
        self._load_weights()
        self.net.to(self.device)
        self.net.eval()

    @abstractmethod
    def _build_architecture(self) -> nn.Module: ...

    @abstractmethod
    def _preprocess(self, image: Image.Image) -> torch.Tensor: ...

    def _load_weights(self) -> None:
        state_dict = torch.load(self.model_path, map_location=self.device)
        # Hỗ trợ cả file lưu toàn bộ checkpoint lẫn chỉ state_dict
        if isinstance(state_dict, dict) and "model" in state_dict:
            state_dict = state_dict["model"]
        self.net.load_state_dict(state_dict)

    @torch.no_grad()
    def predict(self, image: Image.Image) -> dict:
        """
        {
            "probs":      list[float],   # xác suất cho tất cả class
            "top5":       list[int],     # indices top-5
            "top5conf":   list[float],   # confidence top-5
        }
        """
        tensor = self._preprocess(image)
        logits = self.net(tensor)  # (1, num_classes)
        probs = torch.softmax(logits, dim=1)[0]  # (num_classes,)
        top5_confs, top5_indices = torch.topk(probs, k=min(5, len(self.class_names)))

        return {
            "probs": probs.tolist(),
            "top5": top5_indices.tolist(),
            "top5conf": top5_confs.tolist(),
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"device={self.device}, "
            f"num_classes={len(self.class_names)}, "
            f"model_path={self.model_path!r})"
        )


class ResNet50(Model):
    __DROPOUT = 0.35
    __IMGSZ = 384
    __MEAN = [0.485, 0.456, 0.406]
    __STD = [0.229, 0.224, 0.225]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        from torchvision import transforms

        self._transform = transforms.Compose(
            [
                transforms.Resize(self.__IMGSZ + 32),
                transforms.CenterCrop(self.__IMGSZ),
                transforms.ToTensor(),
                transforms.Normalize(self.__MEAN, self.__STD),
            ]
        )

    def _build_architecture(self) -> nn.Module:
        net = models.resnet50(weights=None)
        in_features = net.fc.in_features
        net.fc = nn.Sequential(  # type: ignore
            nn.Dropout(p=self.__DROPOUT),
            nn.Linear(in_features, len(self.class_names)),
        )
        return net

    def _preprocess(self, image: Image.Image) -> torch.Tensor:
        return self._transform(image).unsqueeze(0).to(self.device)  # type: ignore


class YOLOv8(Model):
    __IMGSZ = 384

    def _build_architecture(self) -> nn.Module:
        return nn.Identity()

    def _load_weights(self) -> None:
        from ultralytics import YOLO

        self._yolo = YOLO(self.model_path)

    def _preprocess(self, image: Image.Image) -> torch.Tensor:
        raise NotImplementedError(
            "YOLOv8 model does not use traditional preprocessing; it processes PIL images directly in predict()"
        )

    def predict(self, image: Image.Image) -> dict:
        """
        {
            "probs":    list[float],
            "top5":     list[int],
            "top5conf": list[float],
        }
        """
        results = self._yolo(image, imgsz=self.__IMGSZ, verbose=False)

        if not results or not results[0].probs:
            raise RuntimeError("YOLO inference failed or returned no probabilities.")

        probs_obj = results[0].probs
        return {
            "probs": probs_obj.data.tolist(),
            "top5": list(probs_obj.top5),
            "top5conf": [float(c) for c in probs_obj.top5conf],
        }


class EnsembleModel:
    """
    Kết hợp nhiều Model bằng Weighted Average trên probability vector.

    Công thức:
        final_probs[i] = Σ (weight[j] * probs[j][i]) / Σ weight[j]
    """

    def __init__(self, members: list[tuple[Model, float]]) -> None:
        """
        Args:
            members: list các tuple (model, weight).
                     weight không cần normalize trước — EnsembleModel tự lo.
        """
        if not members:
            raise ValueError("EnsembleModel requires at least one member model.")

        self.members = members
        self._total_weight = sum(w for _, w in members)

        first = members[0][0]
        self.class_names = first.class_names
        self.mapped_class_names = first.mapped_class_names

    def predict(self, image: Image.Image) -> dict:
        """
        Chạy tất cả model, weighted-average probability, trả về top-5.

        {
            "probs":    list[float],
            "top5":     list[int],
            "top5conf": list[float],
        }
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        n = len(self.class_names)
        blended = [0.0] * n

        with ThreadPoolExecutor(
            max_workers=len(self.members) if len(self.members) > 1 else os.cpu_count()
        ) as executor:
            future_to_weight = {
                executor.submit(model.predict, image): weight
                for model, weight in self.members
            }
            for future in as_completed(future_to_weight):
                weight = future_to_weight[future]
                result = future.result()  # raise nếu model lỗi
                for i, p in enumerate(result["probs"]):
                    blended[i] += weight * p

        blended = [p / self._total_weight for p in blended]
        top5_indices = sorted(range(n), key=lambda i: blended[i], reverse=True)[:5]
        top5_confs = [blended[i] for i in top5_indices]

        return {
            "probs": blended,
            "top5": top5_indices,
            "top5conf": top5_confs,
        }

    def __repr__(self) -> str:
        parts = [f"{m.__class__.__name__}(w={w})" for m, w in self.members]
        return f"EnsembleModel([{', '.join(parts)}])"


resnet50 = ResNet50(
    model_path=os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "model", "resnet50.pt")
    ),
    class_names=CLASS_NAMES,
    mapped_class_names=MAPPED_CLASS_NAMES,
)

yolov8 = YOLOv8(
    model_path=os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "model", "yolov8.pt")
    ),
    class_names=CLASS_NAMES,
    mapped_class_names=MAPPED_CLASS_NAMES,
)

ensemble = EnsembleModel(
    [
        (resnet50, 0.5),
        (yolov8, 0.5),
    ]
)
