# 真实 AI 测试前稳定状态

- Mock Pipeline：通过
- Script-Derived Mock：通过
- 中文输入链：通过
- Codex CLI 登录：通过（本轮不发起请求）
- native_schema：通过
- Structured Schema Preflight：通过
- Stage 01、02：曾经真实成功
- Stage 03 原 Schema 问题：已修复
- gpt-5.6-luna：当前服务端 `model_capacity`
- gpt-5.6-terra：当前服务端 `model_capacity`
- gpt-5.6-sol：当前服务端 `model_capacity`
- Stage 01—06 真实闭环：尚未完成
- GUI 真实 AI 模式：尚未正式验收

## 下一次恢复测试入口

1. 只执行一次最小请求：`codex exec` + `Respond with exactly OK.`
2. 优先选择一个当前可用的官方模型。
3. 最小 OK 成功后，再执行 native_schema 最小测试。
4. 两项都成功后，创建 `第一次真实AI烟雾测试_05`。
5. 只运行 Stage 01—06，并只生成 Seedance 2.0。

不要重做 Mock、中文编码或 Schema 修复，除非新的测试明确证明这些模块再次出现问题。
