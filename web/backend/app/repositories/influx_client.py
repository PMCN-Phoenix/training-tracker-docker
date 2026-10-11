# -*- coding: utf-8 -*-
"""InfluxDB 客户端（健身版：training-org）"""
import urllib.request
import csv
import io
from typing import List, Dict, Any, Optional

INFLUX_URL = "http://127.0.0.1:8086"
INFLUX_ORG = "training-org"
INFLUX_BUCKET = "training"
INFLUX_TOKEN = "training-super-secret-token-2026"


class InfluxDBClient:
    def __init__(self, url: str = INFLUX_URL, org: str = INFLUX_ORG,
                 bucket: str = INFLUX_BUCKET, token: str = INFLUX_TOKEN):
        self.url = url
        self.org = org
        self.bucket = bucket
        self.token = token

    def query(self, flux_query: str) -> List[Dict[str, Any]]:
        """执行 Flux 查询，返回解析后的行列表"""
        url = f"{self.url}/api/v2/query?org={self.org}"
        req = urllib.request.Request(
            url,
            data=flux_query.encode("utf-8"),
            method="POST"
        )
        req.add_header("Authorization", f"Token {self.token}")
        req.add_header("Content-Type", "application/vnd.flux")
        req.add_header("Accept", "application/csv")

        with urllib.request.urlopen(req, timeout=30) as response:
            csv_data = response.read().decode("utf-8")

        return self._parse_csv(csv_data)

    def _parse_csv(self, csv_data: str) -> List[Dict[str, Any]]:
        """解析 InfluxDB 返回的 CSV 数据（跟随每组 table 的 header 行）
        注意：InfluxDB CSV 行尾带 \\r（CRLF），header 与值都必须 rstrip 掉，否则行尾列解析失败。
        """
        header = None
        results = []
        for line in csv_data.strip().split("\n"):
            if line.startswith("#") or not line.strip():
                continue
            if line.startswith(",result"):
                header = [h.rstrip("\r") for h in line.split(",")]
                continue
            if header:
                row = [v.rstrip("\r") for v in line.split(",")]
                if len(row) == len(header):
                    results.append(dict(zip(header, row)))
        return results

    def write(self, line_protocol: str) -> bool:
        """写入 Line Protocol 数据"""
        url = f"{self.url}/api/v2/write?org={self.org}&bucket={self.bucket}"
        req = urllib.request.Request(
            url,
            data=line_protocol.encode("utf-8"),
            method="POST"
        )
        req.add_header("Authorization", f"Token {self.token}")
        req.add_header("Content-Type", "text/plain")

        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status == 204

    def delete(self, predicate: str, start: str = "2016-01-01T00:00:00Z",
               end: str = "2036-01-01T00:00:00Z") -> bool:
        """InfluxDB 2.x delete API"""
        import json
        url = f"{self.url}/api/v2/delete?org={self.org}&bucket={self.bucket}"
        payload = {"start": start, "stop": end, "predicate": predicate}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST"
        )
        req.add_header("Authorization", f"Token {self.token}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status == 204


# 全局客户端实例
db = InfluxDBClient()
