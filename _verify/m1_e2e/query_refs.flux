
from(bucket: "training")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "ppl_reflection" and r.source == "test")
  |> keep(columns: ["_time", "_field", "_value", "id", "date", "direction", "exercise", "set_index", "session_id", "source"])
  |> sort(columns: ["_time"])
