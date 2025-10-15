import io, zipfile, shutil, pathlib
from typing import Dict
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from .config import settings
from .fixer import fix_all

app = FastAPI(title="MCP Fixer API", version="1.0")

@app.get("/health")
def health():
    return {"status":"ok"}

@app.post("/api/v1/fix/json")
async def fix_from_json(payload: Dict[str, str]):
    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY missing")
    if not payload:
        raise HTTPException(status_code=400, detail="Empty payload")
    fixed_map = fix_all(payload)
    out_dir = pathlib.Path(settings.fixed_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for fn, content in fixed_map.items():
        (out_dir / fn).write_text(content, encoding="utf-8")
    return JSONResponse(content=fixed_map)

@app.post("/api/v1/fix/zip")
async def fix_from_zip(file: UploadFile = File(...)):
    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY missing")
    tmp_root = pathlib.Path("/tmp/in")
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    tmp_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(await file.read())) as zf:
        zf.extractall(tmp_root)
    samples: Dict[str,str] = {}
    for p in tmp_root.rglob("*.java"):
        samples[p.stem] = p.read_text(encoding="utf-8")
    if not samples:
        raise HTTPException(status_code=400, detail="No Java files found in zip")
    fixed_map = fix_all(samples)
    out_dir = pathlib.Path(settings.fixed_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for fn, content in fixed_map.items():
        (out_dir / fn).write_text(content, encoding="utf-8")
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        for fn, content in fixed_map.items():
            zf.writestr(fn, content)
    mem.seek(0)
    return StreamingResponse(mem, media_type="application/zip",
                             headers={"Content-Disposition":"attachment; filename=fixed.zip"})
