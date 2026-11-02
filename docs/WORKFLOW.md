# 英文视频 → 中文配音 Web 应用（基于已验证流程）

## 产品目标
把「上传英文/原片视频 → 中文绘本式意译旁白 → 火山引擎 TTS → 保留 BGM 混音 → 下载成片」做成可公网使用的 Web 应用。

## 已验证的人工流程（必须改进的点）
1. 抽音轨 + Whisper 转写 + 画面字幕核对时间轴
2. Demucs 人声/伴奏分离
3. LLM 意译成中文儿童/绘本口吻（非直译）
4. **不要逐句 TTS 再硬贴时间轴**（会造成卡顿拖尾）。应**整段或大段落一次合成**，用停顿控制节奏，再整体对齐/微调。
5. 中文 VO + no_vocals 伴奏混音（旁白时 duck 伴奏），ffmpeg 封装原画面

## 技术约束
- TTS：**火山引擎豆包** `POST https://openspeech.bytedance.com/api/v3/tts/unidirectional`
  - Header: `X-Api-Key`, `X-Api-Resource-Id: seed-tts-2.0`, `X-Api-Request-Id`
  - Body: `req_params.text`, `speaker`（默认 `zh_female_xiaohe_uranus_bigtts`）, `context_texts`（温柔绘本旁白）, `audio_params.format=mp3`, `speech_rate` [-50,100]
  - 响应 NDJSON：拼接 base64 `data` 得到 mp3
- 密钥环境变量：`VOLCENGINE_TTS_KEY`（已有）
- 可选意译：OpenAI 兼容接口，环境变量 `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`（可先做可编辑文稿，LLM 可选）
- 本地可用组件参考：ffmpeg、faster-whisper、demucs

## MVP 范围（必须完成并可部署）
- 简洁中文 UI：上传视频 → 显示任务进度 → 展示英文字幕/时间轴 → 可编辑中文稿 → 一键「整段配音合成」→ 在线预览 + 下载
- 后端任务队列（同进程 asyncio/后台线程即可，注明后续可换 Redis）
- Dockerfile，可一键部署到 Render Web Service（含 ffmpeg；whisper/demucs 用 CPU 小模型或清晰降级策略）
- README：本地运行、环境变量、部署步骤
- 安全：密钥只读环境变量；上传文件隔离；限制大小（如 100MB）

## 成功标准
- `docker build` 可通过；`README` 有 Render 部署说明
- 上传一条短测试片能跑通到可下载 mp4（可用 fixture）
- TTS 为整段/段落合成，不是逐句拼接硬贴
