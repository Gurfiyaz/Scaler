import json
import shutil
from pathlib import Path

from app.services.processing_service import DocumentProcessingService

def main():
    service = DocumentProcessingService()
    
    input_path = Path(r"C:\Users\gurfiyaz basha\Downloads\Red Herring Prospectus.docx")
    out_dir = Path("submission")
    out_dir.mkdir(exist_ok=True)
    
    print("Processing Document...")
    
    # Process the document
    with open(input_path, "rb") as f:
        file_bytes = f.read()
        
    result = service.process_document("Red Herring Prospectus.docx", file_bytes)
    
    print("Processing Complete. Saving results...")
    
    # Save the output DOCX
    output_docx_path = out_dir / "Redacted_Red_Herring_Prospectus.docx"
    record = service._downloads[result.download_id]
    shutil.copy2(record.filepath, output_docx_path)
    
    # Write evaluation/mapping to a JSON file (temporary representation)
    metrics = {
        "status": result.status,
        "filename": result.filename,
        "detections": result.detections,
        "total_detections": result.total_detections,
        "replacements_applied": result.replacements_applied,
        "validation": result.validation.model_dump(),
        "evaluation": result.evaluation.model_dump()
    }
    
    with open(out_dir / "processing_results.json", "w") as f:
        json.dump(metrics, f, indent=2)
        
    print(f"Total Detections: {metrics['total_detections']}")
    print(f"Validation: {metrics['validation']}")
    
if __name__ == "__main__":
    main()
