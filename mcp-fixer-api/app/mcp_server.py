import json, base64, io, zipfile
from mcp.server import Server
from mcp.types import Tool, TextContent
from .config import settings
from .fixer import fix_all

server = Server("mcp-fixer")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="fix_from_json",
            description="Input: JSON map {logical_name->source}. Output: JSON {filename->fixedSource}.",
            inputSchema={"type":"object","additionalProperties":{"type":"string"}}
        ),
        Tool(
            name="fix_from_zipbytes",
            description="Input: base64-encoded zip bytes; Output: base64-encoded zip of fixed files.",
            inputSchema={"type":"object","properties":{"zip_b64":{"type":"string"}},"required":["zip_b64"]}
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "fix_from_json":
        if not settings.openai_api_key:
            return [TextContent(type="text", text=json.dumps({"error":"OPENAI_API_KEY missing"}))]
        fixed = fix_all(arguments)
        return [TextContent(type="text", text=json.dumps(fixed, ensure_ascii=False))]
    if name == "fix_from_zipbytes":
        if not settings.openai_api_key:
            return [TextContent(type="text", text=json.dumps({"error":"OPENAI_API_KEY missing"}))]
        b = base64.b64decode(arguments["zip_b64"])
        buf = io.BytesIO(b)
        with zipfile.ZipFile(buf, "r") as zf:
            samples = {}
            for n in zf.namelist():
                if n.endswith(".java"):
                    logical = n.rsplit("/",1)[-1].replace(".java","")
                    samples[logical] = zf.read(n).decode("utf-8")
        fixed = fix_all(samples)
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for fn, content in fixed.items():
                zf.writestr(fn, content)
        out.seek(0)
        return [TextContent(type="text", text=json.dumps({"zip_b64": base64.b64encode(out.getvalue()).decode()}, ensure_ascii=False))]
    return [TextContent(type="text", text=json.dumps({"error":"unknown tool"}))]

if __name__ == "__main__":
    server.run_stdio()
