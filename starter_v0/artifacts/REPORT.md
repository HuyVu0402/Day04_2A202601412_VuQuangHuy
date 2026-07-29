# Day 04 Lab v2 Report — Research Agent

> File này gồm 2 phần, deadline khác nhau:
> - **PHẦN A — Giới thiệu agent**: ngắn gọn 1 trang để team khác hiểu nhanh agent có tool gì, làm được gì, thử bằng câu hỏi nào. Xong trước 11:30 để làm tài liệu phụ trợ khi demo.
> - **PHẦN B — Chi tiết / Bằng chứng**: bảng đầy đủ (v0–v3, failure, eval, chat) dựa trên log thật. Có thể hoàn thiện sau buổi debate để nộp bài.

## Team

- Team: Day04 Lab Group
- Members: 
Nguyễn Hoàng Sơn - 2A202601939
Nguyễn Đức Mạnh - 2A202601176
Vũ Quang Huy - 2A202601412
Thiều Thị Ngọc Ánh - 2A202601864
- Provider/model: OpenAI GPT-4o-mini (run eval), Gemini 3.5 Flash (thử thêm nhóm case)

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Agent này dùng để hỗ trợ nghiên cứu nhanh bằng cách chọn tool phù hợp cho các tác vụ như tìm tweet, tìm tin web, đọc URL, hỏi lại khi thiếu thông tin, và xác nhận trước khi gửi nội dung ra ngoài. Trong các lần chạy eval, agent đã thể hiện khả năng routing tool và xử lý tình huống clarification/confirmation tương đối ổn định.

**Link dùng thử (truy cập được trong showdown):**

> Có thể dùng local UI hoặc chạy demo trực tiếp từ terminal bằng Streamlit.

## A2. Tool agent có

> Liệt kê các tool agent đang dùng. Mỗi tool 1 dòng: tên + làm được gì.

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| clarify | hỏi lại người dùng khi thiếu thông tin hoặc yêu cầu xác nhận hành động có side effect | không |
| timeline | lấy các bài đăng gần đây của một tài khoản mạng xã hội | không |
| social_search | tìm bài đăng trên mạng xã hội theo từ khóa | không |
| lookup | tìm tin tức/web theo chủ đề và khung thời gian | không |
| fetch | đọc nội dung từ URL đã cho | không |
| format | trình bày dữ liệu đã có thành digest/bullets/sections | không |
| send | chuẩn bị gửi nội dung lên Telegram sau khi được xác nhận | có |
| policy | tra cứu chính sách nội bộ theo nhóm chính sách | có |
| papers | tìm bài báo khoa học trên arXiv | có |
| paper_text | đọc nội dung paper từ arXiv | có |

## A3. Câu hỏi mẫu để thử

> 3–5 câu hỏi/yêu cầu mẫu để team khác tự thử agent ngay.

1. "Tweet mới nhất của Sam Altman là gì?"
2. "Tin tức AI hôm nay có gì nổi bật?"
3. "Đăng bản tin này lên Telegram giúp mình"
4. "Tra cứu chính sách nội bộ về dữ liệu cá nhân cho nghiên cứu AI"
5. "Đọc nội dung tối đa 3 trang của bài arXiv này: https://arxiv.org/abs/1706.03762"

## A4. Kịch bản demo đã rehearse

> Chuẩn bị 3–5 scenario. Mỗi scenario cần cho thấy tool đã làm gì và một thay đổi cụ thể giữa các version.

| Scenario | Tool trace cần thấy | Câu chuyện cải thiện version | Fallback run/transcript |
|---|---|---|---|
| Tìm tweet của tài khoản | timeline với screenname | Phiên bản đầu cần hỏi lại khi thiếu handle; phiên bản sau nên map đúng tên người sang handle | transcript v0_openai_20260729T172740653501 |
| Xác nhận trước gửi Telegram | clarify(response_type=yes_no) | Agent phải dừng trước khi gửi và hỏi xác nhận | transcript v0_openai_20260729T172740653501 |
| Tra cứu chính sách nội bộ | policy với policy_area/data_privacy | Cần dùng policy thay vì lookup khi hỏi về quy định nội bộ | data/eval_group.json |
| Đọc paper từ arXiv | paper_text với arxiv_url/max_pages | Yêu cầu đọc paper cụ thể phải dùng paper_text và không lẫn với fetch | data/eval_group.json |
| Chuyển từ tweet sang tin web | social_search → lookup | Khi ngữ cảnh đổi hướng, agent phải chuyển tool phù hợp | run_eval kết quả v1 base |

---

# PHẦN B — Chi tiết / Bằng chứng

> Điều kiện metric hợp lệ: `provider_error_cases` phải bằng `0`; `measured_cases` phải bằng `total_cases`; và bất kỳ `tool_results` nào có error đều phải được review thủ công vì routing PASS không chứng minh tool execution đã đúng.

## B1. Version evidence

Dữ liệu thực tế từ các run JSON đã có cho thấy v0 bị lỗi provider ở OpenRouter do thiếu API key, trong khi v1 chạy bằng OpenAI đạt kết quả khả quan. Các bản v2/v3 chưa có metric hợp lệ đủ để báo cáo vì các lần chạy group gặp provider quota/rate limit.

| Version | Prompt/tool change | Hypothesis | Metric name | Before | After | Run File |
|---|---|---|---|---:|---:|---|
| v0 | Baseline, không chỉnh prompt/tool | Cần có provider/API key hợp lệ trước khi đánh giá routing | case_accuracy | 0.0 | 0.0 | runs/v0_B_base_openrouter_20260729T160922018029.json |
| v1 | Cải thiện prompt/tool boundary và clarification confirmation | Nếu prompt nêu rõ clarification/confirmation boundary thì routing đúng hơn | case_accuracy | 0.0 | 0.9 | runs/v1_B_base_openai_20260729T172644146863.json |
| v2 | Dùng nhóm eval mới cho policy/papers/paper_text | Nếu tool declaration rõ ràng hơn thì nhóm case sẽ chạy đúng hơn | case_accuracy | chưa có metric hợp lệ | chưa có metric hợp lệ | runs/v2_B_group_gemini_20260729T164935718007.json |
| v3 | Chưa chạy được metric hợp lệ | Cần provider ổn định hơn và quota đủ | case_accuracy | chưa có metric hợp lệ | chưa có metric hợp lệ | chưa có run hợp lệ |

## B2. Failure analysis

Các lỗi thực tế trong run v1 cho thấy agent chủ yếu sai ở hai nhóm: routing tool và boundary/argument.

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| R01_user_tweets_routing | wrong_tool | clarify | Agent chọn clarify thay vì timeline khi thiếu handle, thay vì hỏi đúng kiểu thông tin cần thiết | Cần làm rõ trong prompt rằng nếu user chỉ nêu tên người và không có handle, agent nên ưu tiên mapping tên → handle rồi gọi timeline, thay vì dừng ở clarification quá sớm |
| R12_confirm_before_send | wrong_boundary | clarify(response_type=text) | Agent hỏi kiểu text thay vì yes_no cho hành động gửi | Cần nêu rõ trong system prompt và tools.yaml rằng send phải dùng clarify yes_no trước khi thực hiện |
| R13_parallel_web_and_tweets | wrong_tool | không có lỗi trong run v1 | Đây là case khó nhưng run v1 vẫn pass; cần giữ rule parallel tool use | Giữ nguyên quy tắc cho phép gọi nhiều tool song song khi request có hai nhiệm vụ riêng |

## B3. Team eval cases

Tập eval nhóm đã được thiết kế với 10 case, gồm 5 single-turn và 5 multi-turn, tập trung vào policy, papers, paper_text, format và send confirmation.

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
| G01_policy_data_privacy | tra cứu chính sách bảo mật dữ liệu | policy với policy_area=data_privacy và top_k=2 | thiết kế sẵn trong data/eval_group.json |
| G02_papers_latest_rag | tìm paper theo từ khóa và giới hạn số lượng | papers với query/retrieval augmented generation, max_results=4, sort_by=submittedDate | thiết kế sẵn trong data/eval_group.json |
| G03_read_arxiv_paper_text | đọc paper từ URL arXiv | paper_text với arxiv_url và max_pages=3 | thiết kế sẵn trong data/eval_group.json |
| G04_format_existing_items | trình bày dữ liệu đã có thành bullet | format với template=bullets và headline=AI Brief | thiết kế sẵn trong data/eval_group.json |
| G05_confirm_before_send | xác nhận trước khi gửi Telegram | clarify(response_type=yes_no) | thiết kế sẵn trong data/eval_group.json |
| G06_multiturn_papers_correction | sửa lại request sau khi đổi số lượng và sort order | papers với max_results=3, sort_by=lastUpdatedDate | thiết kế sẵn trong data/eval_group.json |
| G07_multiturn_supply_arxiv_url | cung cấp URL ở lượt sau và giữ giới hạn trang | paper_text với arxiv_url và max_pages=2 | thiết kế sẵn trong data/eval_group.json |
| G08_multiturn_policy_scope_correction | đổi policy area và top_k theo yêu cầu mới | policy với data_privacy + top_k=2 | thiết kế sẵn trong data/eval_group.json |
| G09_multiturn_format_template_correction | đổi template và headline theo lượt sau | format với template=brief và headline=Weekly AI Brief | thiết kế sẵn trong data/eval_group.json |
| G10_multiturn_confirmed_send | gửi nội dung sau khi user xác nhận | send với confirmed=true và text đúng nội dung | thiết kế sẵn trong data/eval_group.json |

## B4. Live chat evidence

Các transcript thực tế cho thấy agent đã chạy được các tương tác đa vòng và xử lý confirmation boundary đúng một phần.

| Scenario/Turn | Version | Tool Calls + Args | Transcript/Run | Outcome |
|---|---|---|---|---|
| User asks for latest tweet of Sam Altman | v0 | timeline(screenname='sama', limit=1) | transcripts/v0_openai_20260729T172740653501.transcript.json | Thành công về routing tool timeline |
| User asks to post to Telegram | v0 | clarify(response_type=yes_no) | transcripts/v0_openai_20260729T172740653501.transcript.json | Agent dừng lại và chờ xác nhận đúng boundary |
| User says 'yes' then asks to send | v0 | send(text=...) | transcripts/v0_openai_20260729T172740653501.transcript.json | Chỉ dừng ở confirmation cần review, không tự gửi trực tiếp |
| Out-of-scope arithmetic request | v0 | no tool | transcripts/v0_openai_20260729T172740653501.transcript.json | Agent từ chối đúng phạm vi |

## B5. Tool capability evidence

Agent hiện có các tool cốt lõi và một số tool mới bổ sung cho nhóm eval. Trong các run thực tế, các tool routing cơ bản như timeline/social_search/lookup/fetch đã hoạt động tốt; các tool mới như policy/papers/paper_text được thiết kế để hỗ trợ nhóm eval nhưng chưa có đủ metric hợp lệ do provider quota/không có API key.

| Category | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| Must-have: tool mới đầu tiên | tools/policy/tool.py | Đã có declaration và route logic cho policy | Cần kiểm tra với provider thật để tránh sai phạm vi |
| Optional built-in | artifacts/tools.yaml | clarify, timeline, social_search, lookup, fetch, format đều có declaration rõ | Cần giữ description ngắn và rõ ràng để tránh over-routing |
| Bonus: tool mới thứ 4 trở đi | tools/papers/tool.py, tools/paper_text/tool.py | Đã có implementation và case eval cho papers/paper_text | Cần provider hỗ trợ và quota đủ để chạy full eval |

## B6. Reflection

- Các sửa đổi nên nằm trong system_prompt.md: quy định về clarification boundary, confirmation before send, switch tool khi context đổi hướng, và quy tắc không gọi tool khi request ngoài phạm vi.
- Các sửa đổi nên nằm trong tools.yaml: làm rõ schema của clarify, timeline, social_search, lookup, send, policy, papers và paper_text, đặc biệt là response_type=yes_no cho clarify và confirmed=true cho send.
- Failure cần review thủ công thay vì chấm tự động: các trường hợp liên quan đến confirmation boundary và out-of-scope, vì chúng cần xem agent có hỏi lại đúng hay xử lý đúng ranh giới an toàn hơn là chỉ nhìn tool name.
- Điểm cần cải thiện tiếp: cần có provider/API key ổn định, giảm lỗi provider_error, làm rõ thêm mapping tên người → handle và mapping chủ đề sang tool phù hợp, rồi chạy lại v2/v3 với metric hợp lệ.
