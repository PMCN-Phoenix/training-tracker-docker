# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\web\backend")
from app.repositories import ppl_reflection_repo as repo

ref_id = repo._generate_reflection_id("2026-10-08")
now_ns = 1700000000000000000
direction, exercise, set_index, source = "push", "平板卧推", 2, "web"
title, tags = None, ["发力感"]
tags_str = ",".join(tags) if tags else ""

tag_parts = [f"id={repo._escape_tag_value(ref_id)}", f"date={repo._escape_tag_value('2026-10-08')}"]
tag_parts.append(f"direction={repo._escape_tag_value(direction)}")
tag_parts.append(f"exercise={repo._escape_tag_value(exercise)}")
tag_parts.append(f"set_index={str(set_index)}")
tag_parts.append(f"source={repo._escape_tag_value(source)}")

field_parts = [f'content="{repo._escape_field_string("补录测试")}"']
field_parts.append(f'tags="{repo._escape_field_string(tags_str)}"')

line = f"ppl_reflection,{','.join(tag_parts)} {' '.join(field_parts)} {now_ns}"
print(repr(line))
