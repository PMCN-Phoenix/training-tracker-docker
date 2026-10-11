
from(bucket: "training")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "ppl_push_bench_flat" and r.source == "test")
  |> keep(columns: ["_time", "_field", "_value", "exercise", "set_index", "session_id", "source"])
