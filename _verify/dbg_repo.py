# -*- coding: utf-8 -*-
import sys, traceback
sys.path.insert(0, r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\web\backend")
from app.repositories import ppl_reflection_repo as repo
try:
    r = repo.create_ppl_reflection(
        content="补录测试", date="2026-10-08", direction="push",
        exercise="平板卧推", set_index=2, tags=["发力感"], source="web")
    print("OK", r)
except Exception:
    traceback.print_exc()
