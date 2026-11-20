from fastapi import APIRouter
from app.routers import auth, users, categories, posts, comments
from app.routers import notifications, ws

api_router = APIRouter(prefix="/api/v1")
from app.routers.autosave import router as autosave_router
api_router.include_router(autosave_router)
for router in (auth.router, users.router, categories.router, posts.router, comments.router, notifications.router, ws.router):
    api_router.include_router(router)
