# AIBOM UV Env Build Skill

该 skill 负责把智能体二准备好的 `AIBOMEnvBuildRequest` 落成一个本地 `uv` Python 实验环境。

对调用方只暴露统一入口：

```python
from backend.agents.wp12_agents.skills.aibom_uv_env_build_skill import (
    run_aibom_uv_env_build_skill,
)

result = run_aibom_uv_env_build_skill(request)
```

边界约束：

- 不做任务选择，只消费结构化 request。
- 不在 skill 层直接编写 SQL。
- 允许通过注入的 repository / service 做局部补查。
- 第一版只支持 `blueprint_only`、`uv_build`、`uv_build_and_seed`。
