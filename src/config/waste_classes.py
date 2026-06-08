CLASS_NAMES = [
    "Battery",
    "Biological",
    "Cardboard",
    "Clothes",
    "E_Waste",
    "Glass",
    "Metal",
    "Paper",
    "Plastic",
    "Other",
]

NUM_CLASSES = 10

CLASS_TO_IDX = {name: idx for idx, name in enumerate(CLASS_NAMES)}
IDX_TO_CLASS = {idx: name for name, idx in CLASS_TO_IDX.items()}

BIN_MAPPING = {
    "Battery": "Hazardous",
    "E_Waste": "Hazardous",
    "Biological": "Organic",
    "Cardboard": "Recyclable",
    "Glass": "Recyclable",
    "Metal": "Recyclable",
    "Paper": "Recyclable",
    "Plastic": "Recyclable",
    "Clothes": "Other",
    "Other": "Other",
}