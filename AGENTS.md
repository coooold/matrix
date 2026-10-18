# 自动开发约定

- 使用当前隔离任务的 checkout；未被用户要求时不要新建 worktree。
- 阅读 README.md、docs/architecture.md 与 docs/omega-development-workflow.md；以 docs/acceptance.json 的固定验收 ID 拆分任务，先写 Given/When/Then，再实现小范围变更。
- 运行 tools/setup.sh，完成后运行 tools/check.sh；打包变更还需构建 wheel。
- GUI 主线程禁止同步文件遍历、网络、搜索、解码和阻塞等待。后台任务必须限并发、限队列或支持取消；模型更新通过 Qt 信号回到 GUI 线程。
- 列表使用虚拟化和复用；特效先测量后引入。不得用平均 FPS 替代 P95/P99，也不得把 offscreen 测试称为硬件性能验收。
- 不实现自有合成器；Wayland/KWin 是既定路线。桌面角色、任务栏协议和全局快捷键使用受支持的 KDE/Wayland 接口，禁止伪装普通窗口为已完成桌面会话。
- 每个 PR 描述行为、测试证据和限制。性能相关 PR 附 docs/performance.md 中的实机捕获；缺失时明确硬件 gate 未执行。
- 不自动合并、发布、安装登录会话或替换用户桌面。仓库 CI 是基础 gate；硬件 gate 必须独立执行。
- OMEGA-OS 是体验基准，固定源码 SHA；真实功能仍用 Linux 后端，模拟值不能用于系统验收。基准变更单独 PR，不随上游 HEAD 漂移。
- PR 使用 .github/PULL_REQUEST_TEMPLATE.md，列出验收 ID 和 ci/kwin/visual/hardware/session 各 gate 的执行结果。未运行写 unrun；每个必需 gate 均有执行证据与人工复核才能标记 verified。
