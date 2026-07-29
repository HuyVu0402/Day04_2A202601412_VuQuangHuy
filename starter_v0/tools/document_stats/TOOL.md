---
name: document_stats
track: core
kind: local
provider: Python
requires_env: []
inputs: [text]
outputs: [word_count, character_count, sentence_count, paragraph_count, estimated_reading_time]
side_effect: false
---

# document_stats

Thống kê các thông tin cơ bản của một văn bản, bao gồm số từ, số ký tự,
số câu, số đoạn văn và thời gian đọc ước tính.
Tool này không chỉnh sửa nội dung và không gọi bất kỳ dịch vụ bên ngoài nào.