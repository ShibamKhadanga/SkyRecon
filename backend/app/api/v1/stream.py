import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/stream", tags=["stream"])


@router.get("/proxy")
async def proxy_stream(url: str):
    """
    Proxies any camera stream URL (MJPEG, HLS, etc.) through the backend.
    This solves CORS — the browser talks to FastAPI, FastAPI talks to the camera.
    Usage: /api/v1/stream/proxy?url=http://192.168.1.6:8080/video
    """
    try:
        client = httpx.AsyncClient(timeout=None, follow_redirects=True)
        req = client.build_request("GET", url)
        upstream = await client.send(req, stream=True)

        if upstream.status_code not in (200, 206):
            raise HTTPException(status_code=502, detail=f"Camera returned {upstream.status_code}")

        content_type = upstream.headers.get("content-type", "video/mp4")

        return StreamingResponse(
            upstream.aiter_raw(),
            status_code=upstream.status_code,
            media_type=content_type,
            headers={
                "Cache-Control": "no-cache",
                "Access-Control-Allow-Origin": "*",
            },
            background=None,
        )
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="Cannot reach camera. Check the IP and ensure camera is on same network.")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Camera connection timed out.")
