import torch
import warnings
import sys

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

print("Installing required packages...")
# Note: You need to install torchreid in your Kaggle environment first if not installed:
# !pip install git+https://github.com/KaiyangZhou/deep-person-reid.git

try:
    from torchreid.models import build_model
except ImportError:
    print("ERROR: torchreid is not installed.")
    print("Please run this in a Kaggle notebook cell first:")
    print("!pip install git+https://github.com/KaiyangZhou/deep-person-reid.git")
    sys.exit(1)

def export_osnet():
    print("\n--- Exporting OSNet for Asset Re-Identification ---")
    
    # 1. Build the OSNet model (we'll use osnet_x1_0, a strong baseline)
    # This automatically downloads pretrained weights for person ReID
    # We will repurpose its powerful feature extraction for assets.
    print("1. Downloading and building pretrained OSNet...")
    model = build_model(
        name='osnet_x1_0',
        num_classes=1000,
        loss='softmax',
        pretrained=True
    )
    
    # We only need the feature extractor (backbone), not the classification head
    model.eval()
    
    # 2. Create a dummy input matching our planned crop size (256x256 square for vehicles)
    print("2. Creating dummy input (Batch=1, Channels=3, Height=256, Width=256)...")
    dummy_input = torch.randn(1, 3, 256, 256)
    
    # 3. Export to ONNX
    output_path = "reid_backbone_best.onnx"
    print(f"3. Exporting to {output_path}...")
    
    torch.onnx.export(
        model, 
        dummy_input, 
        output_path,
        export_params=True,
        opset_version=11,          # Standard, stable opset
        do_constant_folding=True, 
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={
            'input': {0: 'batch_size'},
            'output': {0: 'batch_size'}
        },
        dynamo=False               # Force legacy exporter — avoids onnxscript dependency on PyTorch 2.x
    )
    
    print(f"\n✅ Export complete! Please download '{output_path}' and place it in 'models/reid/'.")

if __name__ == "__main__":
    export_osnet()
