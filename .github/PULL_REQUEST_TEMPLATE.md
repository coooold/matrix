## 用户行为与验收范围

解决什么问题，用户操作前后有什么变化？

- 验收 ID（见 docs/acceptance.json）：
- 当前阶段：
- 明确不包含的范围：

## 实现与证据

- Matrix 提交 SHA：
- OMEGA 基准 SHA（基准变化需说明差异）：
- 测试环境、命令、结果与原始证据链接：

| Gate | 是否必需及原因 | 结果（passed/failed/unrun） | 证据 |
| --- | --- | --- | --- |
| ci | 必需 | unrun | |
| kwin | | unrun | |
| visual | | unrun | |
| hardware | | unrun | |
| session | | unrun | |

## 限制与回归

- 异常/空状态/取消/恢复路径：
- 视觉变更的前后截图及 golden 更新理由：
- 剩余缺口；硬件 gate 未运行时明确“未验收”：

offscreen、截图或模拟数据不能证明真实会话、系统指标、安全锁屏或硬件流畅度。更新 verified 状态前需执行证据和人工复核。
