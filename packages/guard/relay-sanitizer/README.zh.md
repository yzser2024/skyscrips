---
description: "Strips the content fingerprints a local relay reads as evidence of a non-official client from every assembled system prompt."
kind: "package-reference"
---

# @deepseek-ai/dsh-relay-sanitizer

让装配好的 system prompt 不再带有本地反代判定「非官方客户端」时依据的内容指纹。

反代面对上游网关时，靠两类证据判断请求像不像官方客户端：字面内容指纹，以及请求形态。上游扫描 `system`、`developer`、`assistant` 三种角色，工具描述也扫，所以指纹能经三条路径上线——system prompt、工具 schema、以及已经写进会话日志的消息，这三条没有任何单个 prompt 段能一次覆盖。

本插件处理第一条路径。它挂在 `system-prompt/assemble` 这个每次装配都经过的 waterfall 上，在调用方渲染之前改写各段文本。改写装配结果而不是改写贡献它的各个段，意味着一次转换就同时覆盖 armor 正文、harness 身份开场白、工具说明段落，以及部署方后来自己加的段。

## 配置

```yaml
- id: relay-sanitizer
  name: '@deepseek-ai/dsh-relay-sanitizer'
  config:
    logRewrites: false
    phrases: true
```

| 字段 | 默认 | 含义 |
|---|---|---|
| `logRewrites` | `false` | 每次改写装配后记一行，写明触发的规则类别。计数每轮都相同，所以只作调试用。 |
| `phrases` | `true` | 是否改写短语级 n-gram。接官方 API 而不是反代时关掉它，prompt 保持逐字节不变。 |

## 规则

规则表在 `src/rules.ts`，每条都带原因。

| 类别 | 作用范围 | 效果 |
|---|---|---|
| 控制 token | 装配文本 | 剥掉 ChatML 与角色包装 token（`<\|im_start\|>`、`<\|endoftext\|>`、`[INST]` 等），保留周围的可见指令。网关遇到这类 token 会直接拒掉请求。 |
| Marker | 装配文本 | 三句官方客户端横幅改写，语义不变。网关在任意位置匹配这些句子。 |
| 开场指纹 | 装配文本 | harness 身份开场白和另外两句客户端开场白改写。网关只在 offset 0 匹配，而那就是排在 `HARNESS_IDENTITY` 的段。 |
| 身份声明 | 装配文本 | `DeepSeek Harness` 及其各种拼写折叠为 `DeepSeek`。折叠排在短语规则之后，避免前半段和后半段分别折叠后重新拼出 marker。 |
| 短语 n-gram | 装配文本 | `workspace root` → `workspace r00t`。网关是在长句里匹配这个短语的，单个词或半句都能过，所以要改的单位是整个短语。 |
| 裸 at 符号 | 装配文本 | `" @ "` 换成全角形式，模型读起来一样。 |

`user` 角色永远不改写。它装的是用户真正问的东西，网关也不扫它。

## 模型体验

被打码后的文本就是会话日志记下的文本，所以回放和压缩读到的与模型读到的完全一致，恢复会话时不会重新渲染出与计费时不同的 prompt。转换是幂等的：对已经打码的文本再打一次不变，所以从日志重建的 prompt 是稳定的。

每条规则都是字面替换，因此一条被拒的请求只要文本来自操作者的散文——写进 prompt 的文档、被引用的工具输出——也按同样的方式修好，与随包提供的段没有区别。代价是每轮扫一遍装配。

## 已知限制与后续工作

- system prompt 之外的消息文本不改写。用户自己贴进 `user` 轮的指纹原样上线，这是设计如此：改用户自己的话属于网关并不要求的内容变更。
- 规则表写的是实测到的网关匹配项。网关新增一条指纹就要加一条规则，没有任何东西会自行推断。
- 请求形态（`tool_choice` 用字符串、不传 `reasoning_effort: "off"`、`tool_choice: "none"` 时删 `tools`）归序列化请求的适配器管，不属于本插件。
