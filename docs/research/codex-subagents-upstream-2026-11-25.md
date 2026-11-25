# Наблюдение за subagents в Codex: состояние upstream на 2026-11-25

Дата проверки: **2026-11-25**. Цель этого отчёта — определить, может ли Orbita через документированные публичные контракты получить дерево нативной делегации Codex, не разбирая вывод терминала, приватное хранилище Codex или недокументированный UI IPC.

## Короткий вывод

В локальном Codex CLI **0.171.0** есть типы, способные представить делегацию: `Thread.parentThreadId`, subagent-источники потока, `collabAgentToolCall` и `subAgentActivity`. Однако проведённая Orbita прямая проверка увидела завершение дочернего turn, но не получила ни родительского ребра, ни spawn/activity item. Следовательно, наличие типов не доказывает наблюдаемость полного дерева, и профиль 0.171.0 остаётся **не квалифицированным для hierarchy UI**.

Текущая документация App Server описывает перспективный публичный путь восстановления: явное включение subagent `sourceKinds`, `thread/read`, пагинация `thread/turns/list` и `thread/items/list`, а при `experimentalApi: true` — фильтры `parentThreadId`/`ancestorThreadId`. Это надо проверять на конкретном выпущенном CLI с постоянным одноразовым thread. Ветка `main` репозитория уже содержит реализацию этих путей, но является невыпущенным движущимся источником и не может автоматически расширить контракт закреплённой 0.171.0.

Готовое upstream-решение с явным multi-agent lifecycle существует в облачном **Agents API**. Оно не является drop-in заменой локальному App Server: меняет границу исполнения, аутентификацию, биллинг, хранение и privacy-модель. Для текущей локальной Orbita рекомендация — оставить MVP на корневых задачах и не показывать фиктивную иерархию; отдельно квалифицировать следующий стабильный Codex. Переход на Agents API возможен только как отдельное продуктовое решение и ADR.

## Проверенный baseline Orbita

- Локальный бинарник: `codex-cli 0.171.0`; профиль и хэши зафиксированы в [`compatibility-profile-0.171.0.md`](../protocol/compatibility-profile-0.171.0.md).
- Официальный релиз: [`rust-v0.171.0`](https://github.com/openai/codex/releases/tag/rust-v0.171.0), исходный commit [`ccf9be8cc458bd6b8336fe84d68d8893f2691a5e`](https://github.com/openai/codex/commit/ccf9be8cc458bd6b8336fe84d68d8893f2691a5e).
- Публичный контракт релиза: [App Server README 0.171.0](https://github.com/openai/codex/blob/rust-v0.171.0/codex-rs/app-server/README.md) и [сгенерированные TypeScript bindings 0.171.0](https://github.com/openai/codex/tree/rust-v0.171.0/codex-rs/app-server-protocol/schema/typescript).
- Прямая проверка Orbita: [`live-delegation-0.171.0.json`](../../spikes/app-server-probe/fixtures/live-delegation-0.171.0.json). Она запускала public App Server по stdio с `multi_agent_v2`, `approvalPolicy: never`, read-only sandbox и ephemeral root. Был замечен дочерний `turn/completed`, но `spawnReceiverIdentities` и `subAgentActivityIdentities` пусты, а итог — `missingDirectParentEdge`.

Последний пункт — отрицательный факт только для проверенного сценария, а не утверждение, что Codex никогда не отдаёт ребро. Но его достаточно, чтобы **не разрешать** hierarchy capability в текущем профиле.

## Что подтверждено публичными контрактами 0.171.0

Сгенерированные bindings локального бинарника и [закреплённые upstream bindings](https://github.com/openai/codex/tree/rust-v0.171.0/codex-rs/app-server-protocol/schema/typescript/v2) подтверждают следующее.

1. `Thread.parentThreadId: string | null` — стабильное поле. Комментарий схемы связывает ненулевое значение с subagent thread. `Thread` также содержит `source`, `agentNickname` и `agentRole`.
2. `SubAgentSource.thread_spawn` способен нести `parent_thread_id`, depth, agent path, nickname и role.
3. Стабильный `ThreadItem` умеет представлять `collabAgentToolCall` со sender/receiver thread IDs, prompt, status и состояниями агентов, а также `subAgentActivity` с agent thread ID, path и фазой активности.
4. `CollabAgentTool` включает операции spawn/send/resume/wait/close/message/follow-up/interrupt/list; это перечисление модели событий, а не документированный RPC, которым внешний клиент сам запускает нативного subagent.
5. В стабильном `thread/list` есть `sourceKinds`, но нет relation-фильтров. В экспериментальном варианте bindings 0.171.0 присутствуют `parentThreadId` и `ancestorThreadId`; они требуют `initialize.params.capabilities.experimentalApi: true` и не входят в стабильный профиль Orbita.

Эти факты подтверждают **представимость** делегации. Они не подтверждают, что каждый spawn обязательно транслируется подписанному App Server-клиенту, сохраняется в history и восстанавливается после рестарта.

### Как upstream запускает и показывает subagents

[Официальная документация subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) подтверждает пользовательские поверхности: прямой запрос на делегацию в Codex App, CLI и IDE; просмотр child thread в App; `/subagents` в CLI; background-agent panel в IDE. Локальный Codex делегирует после прямой просьбы пользователя либо соответствующей инструкции из `AGENTS.md`/skill. Child наследует sandbox, approval policy и инструменты parent; невозможность получить новое approval в non-interactive child приводит к ошибке операции.

Это готовые upstream UI, но не протокол для встраиваемого клиента. Для Orbita важно различать:

- **model-facing orchestration tools**, которые вызывает сам Codex внутри turn;
- **App Server RPC/notifications**, которые доступны внешнему host.

[Исходный tool contract 0.171.0](https://github.com/openai/codex/blob/ccf9be8cc458bd6b8336fe84d68d8893f2691a5e/codex-rs/core/src/tools/handlers/multi_agents_spec.rs) подтверждает V2-операции `spawn_agent`, `send_message`, `followup_task`, `wait_agent`, `interrupt_agent` и `list_agents`. `list_agents` возвращает дерево текущего root с canonical task paths и статусами, но это **не App Server RPC для Orbita**. `followup_task` повторно запускает idle child или доставляет follow-up работающему child на безопасной границе; `interrupt_agent` останавливает текущий turn, сохраняя agent/context. Таким образом upstream умеет управлять деревом изнутри модели, однако внешний host всё равно должен наблюдать результат через App Server.

## Публичный App Server: live-наблюдение и backfill

[Актуальная официальная документация App Server](https://learn.chatgpt.com/docs/app-server) задаёт базовый lifecycle `initialize` → `thread/start`/`thread/resume` → `turn/start` → поток notifications/items → `turn/completed`. `thread/start` подписывает создавшее соединение на события нового thread; `thread/read` читает состояние, но не возобновляет thread и не подписывает клиента.

Для discovery/backfill документированы:

- `thread/list`; по умолчанию он не обязан возвращать subagent threads, поэтому клиент должен явно передать subagent `sourceKinds`;
- `thread/read` для метаданных конкретного child;
- `thread/turns/list` с представлением items `notLoaded`/`summary`/`full`;
- `thread/items/list` для пагинации сохранённых items, если активное хранилище поддерживает этот метод;
- экспериментальные фильтры `thread/list.parentThreadId` и `ancestorThreadId` при `experimentalApi: true`.

Следствие для прежней проверки Orbita: ephemeral root был полезен для безопасного live-теста, но недостаточен для проверки persistence/backfill. Новый тест должен использовать постоянный одноразовый thread (`ephemeral: false`) и затем удалить только созданный им тестовый контекст через публичный lifecycle, если версия поддерживает такую операцию.

### Что видно в открытом Rust source

На дату проверки `main` находится на commit [`ebd0765aafa255d63ebf690ebdffe0164dc14a0c`](https://github.com/openai/codex/commit/ebd0765aafa255d63ebf690ebdffe0164dc14a0c), то есть впереди релиза 0.171.0. Это полезное свидетельство направления разработки, но не версия, на которую можно перепинить production.

- [`thread.rs`](https://github.com/openai/codex/blob/main/codex-rs/app-server-protocol/src/protocol/v2/thread.rs) объявляет `sourceKinds` и экспериментальные relation-фильтры.
- [`thread_data.rs`](https://github.com/openai/codex/blob/main/codex-rs/app-server-protocol/src/protocol/v2/thread_data.rs) содержит публичную модель thread с parent relation.
- [`event_mapping.rs`](https://github.com/openai/codex/blob/main/codex-rs/app-server-protocol/src/protocol/event_mapping.rs) преобразует collab spawn и subagent activity в App Server items.
- [`thread_history.rs`](https://github.com/openai/codex/blob/main/codex-rs/app-server-protocol/src/protocol/thread_history.rs) восстанавливает структурированные items из сохранённой истории.
- [`spawn.rs`](https://github.com/openai/codex/blob/main/codex-rs/core/src/agent/control/spawn.rs) реализует создание дочернего агента и связь с родителем внутри core.
- [`multi_agents.rs`](https://github.com/openai/codex/blob/main/codex-rs/tui/src/multi_agents.rs) показывает, что официальный TUI уже умеет представлять multi-agent состояние.

TUI-код не является интеграционным API для Orbita: он работает внутри собственного процесса и не даёт права копировать приватный state или UI IPC. Аналогично, наличие mapping/history-кода в `main` — кандидат для повторного теста выпущенной версии, но не доказательство успешной доставки в 0.171.0.

В current `main` child lifecycle дополнительно поддерживает восстановление открытого descendant graph и cold-load выгруженного child из сохранённой истории. Persisted graph хранит направленное parent→child ребро отдельно от runtime residency: завершённый/прерванный turn не равен удалению child thread. Это видно в [`agent-graph-store`](https://github.com/openai/codex/blob/main/codex-rs/agent-graph-store/src/store.rs) и реализации [`state/runtime/threads.rs`](https://github.com/openai/codex/blob/main/codex-rs/state/src/runtime/threads.rs). Внешний клиент не должен читать этот store напрямую; его публичный путь — App Server discovery/backfill.

Также нельзя смешивать разные связи: `parentThreadId` означает spawned subagent, `forkedFromId` — fork lineage, а experimental `attachedToThreadId` — attachment. Только первое поле годится как ребро дерева делегации.

## MCP, dynamic/custom tools и Codex SDK

App Server документирует MCP status/list/read/call и item `mcpToolCall`. MCP расширяет набор внешних инструментов модели, но не документирует API чтения внутреннего дерева нативных subagents. Поэтому MCP нельзя считать способом восстановить недостающее parent edge.

Экспериментальные dynamic tools позволяют клиенту объявить функцию, получить `item/tool/call` и вернуть результат. На их основе Orbita могла бы построить **собственный** оркестратор, но это уже иной источник истины, а не наблюдение нативной делегации Codex. Такой обход не соответствует текущей границе App Server и не рекомендуется.

[Официальная документация Codex SDK](https://learn.chatgpt.com/docs/codex-sdk) описывает программный запуск, продолжение/возобновление thread и streamed run. Для custom clients, которым нужны auth, history, approvals и поток agent events, документация направляет к App Server. Документированного SDK-контракта discovery дочерних threads или parent/backfill graph нет. Значит SDK не закрывает текущий пробел Orbita.

## Готовая альтернатива upstream: Agents API

Новый managed [Agents API](https://developers.openai.com/api/docs/guides/agents-api/overview) имеет явную [multi-agent модель](https://developers.openai.com/api/docs/guides/agents-api/multi-agent): включение multi-agent в agent config, событие создания subagent, coordination items и публичные операции получения subagents/items. [Observability guide](https://developers.openai.com/api/docs/guides/agents-api/observability) и [session events](https://developers.openai.com/api/docs/guides/agents-api/sessions/events) описывают событийный поток и сохранённую историю.

Это готовое публичное решение именно для hosted multi-agent наблюдаемости. Но оно не является новым методом локального `codex app-server`: это OpenAI-managed API с API project/key, отдельной тарификацией и серверным хранением session data. Поэтому его принятие затронет local-first обещание Orbita, security/privacy документы и ADR границы исполнения.

## Матрица решений

| Вариант | Что подтверждено | Решение для Orbita |
|---|---|---|
| App Server 0.171.0 stable | Типы parent/collab/activity; child completion был виден | Не включать hierarchy: прямой probe не доказал ребро |
| App Server 0.171.0 experimental | Relation-фильтры есть в generated contract | Только отдельный экспериментальный compatibility profile; нужен live/backfill probe |
| App Server текущий `main` | Публичные history/filter/mapping пути присутствуют в source | Следить за релизом; не зависеть от невыпущенного `main` |
| Официальный TUI | Готовое отображение subagent state | Research reference, не API и не источник runtime-данных Orbita |
| Codex SDK | Root-thread automation и streaming | Не документирует нужный child graph |
| MCP/dynamic tools | Расширение инструментов | Не восстанавливает native graph; не подменять им Codex orchestration |
| Agents API | Явные hosted subagents, lifecycle, history и observability | Реальная альтернатива, но только после отдельного product/ADR решения |

## Обязательная повторная проверка перед hierarchy UI

Проверять следует **конкретный стабильный релиз**, а не `main`:

1. Сохранить version, executable hash, generated stable/experimental schemas и feature snapshot.
2. Создать постоянный одноразовый root thread (`ephemeral: false`), включить только актуальный upstream multi-agent feature и заранее подписаться на live events.
3. Вызвать сценарий минимум с двумя child agents, чтобы отличить одиночный побочный turn от делегации.
4. Собрать live `thread/started`, collab spawn item, subagent activity, child turn/item events и terminal outcomes.
5. После завершения вызвать `thread/list` с явным набором всех subagent `sourceKinds`; в experimental-профиле отдельно проверить `parentThreadId` и `ancestorThreadId`.
6. Для каждого найденного child вызвать `thread/read`, затем полностью пропагинировать `thread/turns/list` и `thread/items/list` с full items. Дедуплицировать только по публичным ID.
7. Перезапустить App Server и повторить discovery/backfill, если Orbita собирается заявлять recovery после рестарта.
8. Считать parent edge подтверждённым только при совпадении как минимум двух публичных свидетельств, например receiver ID spawn item и `Thread.parentThreadId`. Отдельно потребовать assignment/prompt, activity и авторитетный terminal outcome.
9. Любой unsupported method, пропавший edge, неполная пагинация или child без однозначного parent оставляет capability выключенной.

Тест не должен читать rollout JSONL/SQLite/private storage, разбирать текст терминала или обращаться к TUI IPC.

## Неопределённости

- Почему именно в 0.171.0 child `turn/completed` дошёл, но parent/spawn/activity не дошли: feature configuration, ephemeral lifecycle, race доставки или дефект конкретной версии — не установлено.
- Гарантирует ли будущий стабильный релиз сохранение всех collab/activity items и их восстановление после рестарта — до release-specific probe не подтверждено.
- Названия item variants в текущей веб-документации и generated bindings могут дрейфовать; адаптер Orbita должен строиться из схем закреплённого бинарника, а не из примера на сайте.
- Доступность `thread/items/list` зависит от активного store и должна проверяться как capability.
- Нельзя утверждать, что Agents API сохранит все локальные свойства App Server; это иной runtime и требует отдельного spike.

## Конкретная рекомендация

Для ближайшей полезной версии Orbita сохранить App Server 0.171.0 как квалифицированный root-task runtime и **заморозить subagent hierarchy UI**: не создавать child rows из эвристик и не показывать неподтверждённые parent edges. Подготовить отдельный compatibility probe по описанной матрице для первого стабильного Codex-релиза, где публичный backfill проходит end-to-end. Включать hierarchy только feature-gated профилем после положительного live + restart/backfill результата.

Если обязательным продуктовым требованием становится немедленная полная multi-agent наблюдаемость, рассматривать Agents API отдельной веткой архитектуры с новым ADR по cloud execution, credentials, billing, retention и privacy — не как скрытую замену локального App Server.
