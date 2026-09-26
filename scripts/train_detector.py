"""
Dataset Collection & Training Script — YOLOv8 Construction Equipment Detector

This script handles:
1. Downloading a construction equipment dataset from Roboflow
2. Training YOLOv8n on the dataset
3. Evaluating the trained model
4. Exporting to ONNX for Pi 5 deployment

HOW TO USE:
===========

STEP 1: Get a free Roboflow API key
   - Go to https://app.roboflow.com
   - Sign up (free)
   - Go to Settings → API Keys → Copy your Private API Key

STEP 2: Choose a dataset from Roboflow Universe
   Good options for construction equipment:
   - https://universe.roboflow.com/construction-5bl7x/construction-equipment-93pvb
   - https://universe.roboflow.com/jspark/230620_heavyequipment
   - https://universe.roboflow.com/research/rm-project---combined-dataset
   
   Search more at: https://universe.roboflow.com (search "construction equipment")

STEP 3: Run this script
   python scripts/train_detector.py --api-key YOUR_KEY --workspace WORKSPACE --project PROJECT --version 1

STEP 4: Or skip Roboflow and use a local dataset
   python scripts/train_detector.py --local-dataset path/to/dataset/data.yaml

"""

import argparse
import os
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def download_roboflow_dataset(api_key: str, workspace: str, project: str, version: int, output_dir: str):
    """
    Download a dataset from Roboflow Universe in YOLOv8 format.
    """
    try:
        from roboflow import Roboflow
    except ImportError:
        print("Installing roboflow package...")
        os.system(f"{sys.executable} -m pip install roboflow")
        from roboflow import Roboflow

    print(f"\n[Dataset] Connecting to Roboflow...")
    rf = Roboflow(api_key=api_key)

    print(f"[Dataset] Downloading: {workspace}/{project} v{version}")
    project_obj = rf.workspace(workspace).project(project)
    version_obj = project_obj.version(version)

    dataset = version_obj.download("yolov8", location=output_dir)
    print(f"[Dataset] Downloaded to: {output_dir}")

    return dataset


def train_yolo(data_yaml: str, model_size: str = "yolov8n.pt", epochs: int = 50,
               imgsz: int = 640, batch: int = 16, device: str = "cpu",
               output_dir: str = "runs/detect/train"):
    """
    Train YOLOv8 on the dataset.

    Args:
        data_yaml: Path to data.yaml file
        model_size: Pretrained model to start from (yolov8n.pt = nano, fastest)
        epochs: Number of training epochs
        imgsz: Input image size
        batch: Batch size (reduce if running out of memory)
        device: "cpu" or "0" for GPU
        output_dir: Where to save training results
    """
    from ultralytics import YOLO

    print("\n" + "=" * 60)
    print("  YOLO Training Configuration")
    print("=" * 60)
    print(f"  Model:      {model_size}")
    print(f"  Dataset:    {data_yaml}")
    print(f"  Epochs:     {epochs}")
    print(f"  Image Size: {imgsz}")
    print(f"  Batch Size: {batch}")
    print(f"  Device:     {device}")
    print(f"  Output:     {output_dir}")
    print("=" * 60)

    # Load pretrained model
    model = YOLO(model_size)

    # Train
    print("\n[Training] Starting training...")
    start_time = time.time()

    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project=str(Path(output_dir).parent),
        name=Path(output_dir).name,
        exist_ok=True,
        verbose=True,
        # Performance settings for CPU training
        workers=2,           # Reduce workers for CPU
        cache=True,          # Cache images in RAM for faster training
        # Augmentation (reasonable defaults for construction equipment)
        hsv_h=0.015,         # Hue augmentation
        hsv_s=0.7,           # Saturation augmentation
        hsv_v=0.4,           # Value (brightness) augmentation
        degrees=5.0,         # Rotation
        translate=0.1,       # Translation
        scale=0.5,           # Scale
        fliplr=0.5,          # Horizontal flip
        flipud=0.0,          # No vertical flip (equipment doesn't flip upside down)
        mosaic=1.0,          # Mosaic augmentation
    )

    elapsed = time.time() - start_time
    print(f"\n[Training] Complete! Time: {elapsed / 60:.1f} minutes")

    return model, results


def evaluate_model(model, data_yaml: str):
    """Run validation and print metrics."""
    print("\n[Evaluation] Running validation...")

    metrics = model.val(data=data_yaml, verbose=True)

    print("\n" + "=" * 60)
    print("  Validation Results")
    print("=" * 60)
    print(f"  mAP@0.5:      {metrics.box.map50:.4f}")
    print(f"  mAP@0.5:0.95: {metrics.box.map:.4f}")
    print(f"  Precision:     {metrics.box.mp:.4f}")
    print(f"  Recall:        {metrics.box.mr:.4f}")

    # Per-class results
    if hasattr(metrics.box, 'ap_class_index'):
        print("\n  Per-Class AP@0.5:")
        names = metrics.names
        for i, idx in enumerate(metrics.box.ap_class_index):
            class_name = names[idx] if idx in names else f"class_{idx}"
            ap = metrics.box.ap50[i]
            print(f"    {class_name:20s}: {ap:.4f}")

    print("=" * 60)
    return metrics


def export_model(model, format: str = "onnx", imgsz: int = 640):
    """
    Export the trained model for edge deployment.
    """
    print(f"\n[Export] Exporting model to {format.upper()} format...")

    export_path = model.export(
        format=format,
        imgsz=imgsz,
        simplify=True,      # Simplify ONNX graph
        dynamic=False,       # Static input size (faster inference on Pi)
    )

    print(f"[Export] Model exported to: {export_path}")

    # Copy to our models directory
    dest_dir = PROJECT_ROOT / "models" / "detection"
    dest_dir.mkdir(parents=True, exist_ok=True)

    import shutil
    dest_path = dest_dir / f"yolo_best.{format}"
    shutil.copy2(export_path, str(dest_path))
    print(f"[Export] Copied to: {dest_path}")

    # Also copy the .pt weights
    best_pt = Path(model.trainer.best) if hasattr(model, 'trainer') else None
    if best_pt and best_pt.exists():
        shutil.copy2(str(best_pt), str(dest_dir / "yolo_best.pt"))
        print(f"[Export] PyTorch weights copied to: {dest_dir / 'yolo_best.pt'}")

    return dest_path


def main():
    parser = argparse.ArgumentParser(
        description="Train YOLOv8 Construction Equipment Detector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download from Roboflow and train
  python scripts/train_detector.py --api-key YOUR_KEY --workspace construction-5bl7x --project construction-equipment-93pvb --version 1

  # Train on a local dataset
  python scripts/train_detector.py --local-dataset path/to/data.yaml

  # Train with custom settings
  python scripts/train_detector.py --local-dataset data.yaml --epochs 100 --batch 8 --device 0
        """
    )

    # Dataset source (choose one)
    parser.add_argument("--api-key", type=str, help="Roboflow API key")
    parser.add_argument("--workspace", type=str, help="Roboflow workspace name")
    parser.add_argument("--project", type=str, help="Roboflow project name")
    parser.add_argument("--version", type=int, default=1, help="Roboflow dataset version")
    parser.add_argument("--local-dataset", type=str, help="Path to local data.yaml file")

    # Training settings
    parser.add_argument("--model", type=str, default="yolov8n.pt",
                        help="Base model (default: yolov8n.pt = nano)")
    parser.add_argument("--epochs", type=int, default=50,
                        help="Training epochs (default: 50)")
    parser.add_argument("--batch", type=int, default=16,
                        help="Batch size (default: 16, reduce for CPU)")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Input image size (default: 640)")
    parser.add_argument("--device", type=str, default="cpu",
                        help="Device: 'cpu' or '0' for GPU")

    # Actions
    parser.add_argument("--export-only", action="store_true",
                        help="Skip training, just export an existing model")
    parser.add_argument("--eval-only", action="store_true",
                        help="Skip training, just evaluate an existing model")

    args = parser.parse_args()

    # Determine dataset path
    data_yaml = None
    dataset_dir = str(PROJECT_ROOT / "data" / "datasets" / "construction_equipment")

    if args.local_dataset:
        data_yaml = args.local_dataset
        print(f"[Setup] Using local dataset: {data_yaml}")

    elif args.api_key and args.workspace and args.project:
        download_roboflow_dataset(
            api_key=args.api_key,
            workspace=args.workspace,
            project=args.project,
            version=args.version,
            output_dir=dataset_dir
        )
        data_yaml = os.path.join(dataset_dir, "data.yaml")

    else:
        print("ERROR: Please provide either --local-dataset or Roboflow credentials")
        print("       (--api-key, --workspace, --project)")
        print("\nFor help: python scripts/train_detector.py --help")
        sys.exit(1)

    if not os.path.exists(data_yaml):
        print(f"ERROR: data.yaml not found at: {data_yaml}")
        sys.exit(1)

    # Train
    output_dir = str(PROJECT_ROOT / "runs" / "detect" / "train")

    if not args.export_only and not args.eval_only:
        model, results = train_yolo(
            data_yaml=data_yaml,
            model_size=args.model,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            device=args.device,
            output_dir=output_dir,
        )

        # Evaluate
        evaluate_model(model, data_yaml)

        # Export
        export_model(model, format="onnx", imgsz=args.imgsz)

    elif args.eval_only:
        from ultralytics import YOLO
        best_path = Path(output_dir) / "weights" / "best.pt"
        if not best_path.exists():
            print(f"ERROR: No trained model found at {best_path}")
            sys.exit(1)
        model = YOLO(str(best_path))
        evaluate_model(model, data_yaml)

    elif args.export_only:
        from ultralytics import YOLO
        best_path = Path(output_dir) / "weights" / "best.pt"
        if not best_path.exists():
            print(f"ERROR: No trained model found at {best_path}")
            sys.exit(1)
        model = YOLO(str(best_path))
        export_model(model, format="onnx", imgsz=args.imgsz)

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
