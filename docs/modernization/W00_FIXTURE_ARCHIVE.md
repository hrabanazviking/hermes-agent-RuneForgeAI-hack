# W00.05 — Compatibility Fixture Archive + COMPAT_MANIFEST Fate (Team 01)

Campaign: Hermes Modernization (2026-11-07). Wave W00 closure slice.
Base tree: banked main f7f6a56a2442661896fe8b4fbb54aa2e21c95de0
(W01–W13 all banked). Host: purplelongship, worktree ~/hermes-team-01,
branch yrsa/hermes-team-01, fast-forwarded cleanly to the banked main
before this audit (0 ahead / 21 behind, merge was a pure fast-forward).
Date: 2026-11-08. README.md untouched (sha256
336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3).

## Method

- Inventory from git alone: `git ls-files` on the banked tree (every
  listed file is tracked; there are no untracked fixture files in the
  audited directories — the worktree was clean at audit start).
- Sizes from `du -cb` over the tracked lists; hashes are per-file
  SHA-256 (`sha256sum`), reproduced in the appendix and in the archive
  manifest below, so any future tree can be re-verified byte-for-byte.
- Provenance from git set-membership and tree diffs against three
  pins: last pre-intake merge-base 6bb377a51d, the upstream v0.23.0
  pin 2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19, and the freeze
  281843f10fb0d2c6ca6ee7dab9e99070f7e141ba. Where provenance cannot be
  determined from git evidence it is labelled as such; nothing here is
  guessed.

## Fixture sets in the banked tree

The three sets named by the W00 ticket, plus every other tracked
fixture directory found in the tree:

| Set | Files | Bytes | Purpose (evidence) |
|---|---|---|---|
| tests/fixtures | 48 | 469,409 | Golden test data: prompt-surface prompts/tools snapshots, provider wire snapshot, speech corpus, session/update corpora, example dashboard plugin (paths self-describe; consumed by the test suite) |
| tests/_fixtures | 5 | 44,556 | Shared test helpers: env filter, live-system guard, model peer, platform gating (module names + tests/_fixtures/__init__.py) |
| tests/compat | 4 | 92,292 | Updater compatibility contract: frozen pre-PM updater surface (old_updater_surface.json) + shims; fully self-documented in tests/compat/README.md (kept verbatim in the tree) |
| tests/gateway/fixtures | 65 | 442,078 | Gateway peer/daemon/worker harness processes for gateway contract tests (file names self-describe: *_peer.py, *_daemon.py, *_worker.py, *_probe.py) |
| tests/hermes_cli/fixtures | 2 | 641 | Legacy plugin-compat fixture plugin (plugin_compat_legacy/plugin.yaml + __init__.py) for plugin historic-compat tests |
| tests/plugins/fixtures | 1 | 3,186 | Kanban touch/drag probe script for plugin UI tests |
| **Total, fixture directories** | **125** | **1,052,162** | |

Of these, the W00-named core (tests/fixtures + tests/_fixtures +
tests/compat) is 57 files / 606,257 bytes.

Wider counts, for scale: 154 tracked files anywhere in the tree carry
`fixture` in their path (1,118,412 bytes total — loose files such as
tests/pm/_fixtures.py, evals/*/fixtures.py, desktop e2e fixtures);
179 tracked paths match `fixture` or `compat` (the difference is the
compat test modules and compat source modules, which are code, not
fixture data). No fixtures exist under plugins/volmarr-core or the
other fork plugins (the only fixture-named plugin path is upstream's
plugins/config_backends/remote/vendor/conformance/config-fixtures.sha256).

## Provenance — evidenced, not assumed

- File counts in every audited set are identical at the merge-base
  6bb377a51d, at the upstream v0.23.0 pin, and at the freeze.
- `git diff 2bd378ed1b (pin) HEAD -- <all six sets>` is EMPTY: every
  one of the 125 archived files is byte-identical to the upstream
  v0.23.0 pin. Widened to every tracked path matching fixture/compat,
  the only path that differs from the pin is the fork's own
  docs/modernization/ADAPTER_COMPATIBILITY_MATRIX.md (a document, not
  a fixture).
- The freeze tree differed from the pin in exactly 2 core files
  (tests/_fixtures/env_filter.py, tests/fixtures/resolution_allowlist.json)
  and 4 gateway fixture files; the W01 intake aligned all of them to
  the pin versions, which is what HEAD carries.
- Verdict: the compatibility fixture corpus is UPSTREAM-authored
  (NousResearch hermes-agent), carried unchanged by the fork. No
  fork-authored fixture file was found in any audited set. Per-file
  authorship beyond this tree-level proof (individual blame lines)
  was not needed and is not claimed.

## Archive (outside the repo, per size/binary rule)

- Archive: ~/hermes-backups/2026-11-08-w00-fixtures/hermes-fixtures-f7f6a56.tar.gz
  - 189,793 bytes, 125 entries (exactly the six sets above, paths as
    in the appendix), created with `tar -czf ... -T fixture_list`
    from the banked tree at f7f6a56a24.
  - SHA-256: fcdc47c1c320a8ae7e1b54d92def8e1992a67762ed27567346aff752590d70da
- Manifest: ~/hermes-backups/2026-11-08-w00-fixtures/fixture-manifest-sha256.txt
  - SHA-256: 2dc4a8c5c29f4ef3151454f4ff923cc226ccc1b43cfba6f6e52600b427fb53e8
  - Content is reproduced in the appendix below.
- Reproduce / verify: in any checkout of f7f6a56a24, run
  `git ls-files tests/fixtures tests/_fixtures tests/compat tests/gateway/fixtures tests/hermes_cli/fixtures tests/plugins/fixtures | sort | xargs sha256sum`
  and compare with the appendix; or extract the tarball and run
  `sha256sum -c fixture-manifest-sha256.txt` inside it.

## COMPAT_MANIFEST.md — evidenced fate

Earlier ticks recorded the file as absent at every path in HEAD and
its removal commit as undetermined (a blobless --all history search
timed out and was not retried). This audit searched HEAD ancestry
with pathspec history (fast on this partial clone) and the fate is
now fully evidenced:

- ABSENT in HEAD: confirmed again — `git ls-tree -r HEAD` has no
  COMPAT_MANIFEST.md at any path, and the file is also absent at the
  freeze 281843f10f, at the v0.23.0 pin 2bd378ed1b, and at the
  merge-base 6bb377a51d.
- IT DID EXIST, upstream only: 10 commits in HEAD ancestry touch
  COMPAT_MANIFEST.md (repo root). Name variants searched with zero
  history: COMPATIBILITY_MANIFEST.md, compat-manifest.md,
  COMPAT-MANIFEST.md, docs/COMPAT_MANIFEST.md.
- CREATED in 2776813df3b3f404611c633a9d1f3a087f337f8d —
  "compat(plugins): temporary import-path shims for external plugins
  — ONE commit, revert on schedule" (Teknium, 2026-09-03). The file
  was the manifest for a deliberately temporary upstream plugin
  import-compat layer.
- DELETED in a5bd246865bda88feb84d3289e76deabaece0ece —
  "Old pre-decomposition import paths are gone: plugin compat layer
  removed on schedule (#126164)" (Teknium, 2026-09-28). That commit
  removed COMPAT_MANIFEST.md (3,857 lines), its machine twin
  compat_manifest.json (12,510 lines — also absent in HEAD), and
  tests/hermes_cli/test_compat_manifest_targets.py together.
- Both the creation and the deletion are ancestors of the v0.23.0
  pin and of the freeze: the file lived (2026-09-03 → 2026-09-28)
  and died entirely inside upstream, before the fork's freeze. Its
  last live version is at a5bd246865^ (fe18e71863), 159,172 bytes,
  recoverable from git history if ever needed.
- The fork never authored, carried, or deleted this file. The only
  fork-side trace is documentary: the historical CAMPAIGN_STATE.md
  notes it as a plugin-compat-pointer manifest holding no
  project-state facts. No restoration is warranted: its subject
  (temporary upstream import shims) was retired on schedule by
  upstream itself, and the surviving compat surface is the archived
  tests/compat + plugin_compat code above.

## Appendix — per-file SHA-256 manifest (125 files, banked tree f7f6a56a24)

```
f99931d2a8fac38801b0e72ba9d8b4880a5618b4344134a54f9d0947e75d518f  tests/compat/old_updater_dependencies.py
ce89b28d5c8b05a763f31307adf763b8f3df787fab4163682e3f27d02a97fd17  tests/compat/old_updater_support.py
43064bad01a7cfa7c44938da1135fd466db34d4f28737c43d31bc3b5363b85e3  tests/compat/old_updater_surface.json
56fcd5f6eb84b572e7f36d137245c5fb775f1ab1d86170ef4e5943689f2c8277  tests/compat/README.md
21d770a0ea9c6547b7ec805b20f6261897f29e0e92475cc5e241f9eaf9121db2  tests/fixtures/cua_driver_0_9_tools_list.json
22d65abcf8c808b749096ce9992f6d74a9dd1fdbfcb1ffe77cd060f43dae84e5  tests/_fixtures/env_filter.py
a147e113e54833a2260d477dee3020ca23b9c1bd00c4211fb13fd3934b68135b  tests/fixtures/identifier_speech_corpus.json
6f8f2278a097099fafb651a711fc6026b06517e2b27e9a6146f98b45cfcee36b  tests/_fixtures/__init__.py
45bc08c1acdf2bb8710a560b0567f4143976f01935f08d3f618bfa5244f30d4e  tests/fixtures/legacy_desktop/update-marker-be3fd671.mts
2a33a6fdd5872b15fb3342b5aea728e2328c60c5927ed577ed7aa039c5d8a21a  tests/_fixtures/live_system_guard.py
fdfd44bf6cdc7ebe71f5d98121fa8dce55dddc601b1dc5e5667bd3475e881414  tests/_fixtures/model_peer.py
ed4518bfd3c5c2aec876fb59b74d17de5b8d893ffbad3212a9fcbe7afe51efeb  tests/_fixtures/platform_gating.py
2dab745693e498270c700831facdbc8f864f6b7d1ca3866f534069bf6cd3ccce  tests/fixtures/plugin_component_detection.json
1b5811ea64f18b50e718dcba573de805f72500b510c587483ccfc4fced7c8fa5  tests/fixtures/plugins/example-dashboard/dashboard/manifest.json
c61ce3a925cf4aa0897d29d334633ee93b9af6af8766a61f1546eaebe2d60ab1  tests/fixtures/plugins/example-dashboard/dashboard/plugin_api.py
115c4ed22488f48b8444293134653f7839b851ee2f27ba8962e56a0b0ca88973  tests/fixtures/prompt_surface/prompts/cli.claude.txt
fda270a69346284bc393d3661891e97ddfcad04523bc8cbf0a5fe4f2484a2147  tests/fixtures/prompt_surface/prompts/cli-code.claude.txt
f366f78bed1626f529d33c40f06f7849e3dd7992ecec237f92f63c11c8d4b9eb  tests/fixtures/prompt_surface/prompts/cli.gemini.txt
988328ad4ea36f44512be9a306c5f5ada1c8428a7c726a71fc612317106030f1  tests/fixtures/prompt_surface/prompts/cli.gpt.txt
6a3a86f0846a77769f68df0ab0aa7d939002f72b0cf1753e8be63fe6fca8a93a  tests/fixtures/prompt_surface/prompts/cli.hermes.txt
0f5fb0f4936fb11eef50521605c1ed330cef17c88301b3a777686488740f2049  tests/fixtures/prompt_surface/prompts/cron.claude.txt
27d5de2c85c968c1c5f4dae0ce862774cafc9490e590fd1ec425f93d80c7e55d  tests/fixtures/prompt_surface/prompts/desktop.claude.txt
1c7132aec3b37964dffc402b0b70a32901ee8a96c6a6d0c24c312b7183496c0a  tests/fixtures/prompt_surface/prompts/discord.claude.txt
4934bd2d31d2da458e9b8e4b69e710c0568d3f3688accea4369d6f2f39ec4a93  tests/fixtures/prompt_surface/prompts/telegram.claude.txt
4f940d597796a550ef2f5c6b924ff6d762786c7c313a1527350026f9fda0053c  tests/fixtures/prompt_surface/surfaces.json
72930992748b44cbe782d3a2758eafcadfc95c2f95beab60b2ba757fa6e71373  tests/fixtures/prompt_surface/tools/browser_cdp.json
d707c6a2c3c7481043c1dbc4a32c810b32907eea469f80da1eafc7944b19b41c  tests/fixtures/prompt_surface/tools/browser_dialog.json
b717d9427a2dd58cacacae6ec74c8af54a75a8c28d5bff231faa2e05cac7760b  tests/fixtures/prompt_surface/tools/browser_exec.json
4edb4a6c8c3c181641eeb64e62ae08f1208674c40c3992ed70b34e5e637a14bf  tests/fixtures/prompt_surface/tools/clarify.json
bb7940d641cc2bd3e67a5e772fd007a6e24562de703d48af9eef170f2c92825d  tests/fixtures/prompt_surface/tools/delegate_task.json
223f2581eefdbb7af6e294589416d68e141001c6d08994a64e2b7b9b256b3d6e  tests/fixtures/prompt_surface/tools/execute_code.json
241bd2c4570d4a75aaa5894b35551eeeb6b84d1f809049e857c63f0eb066c698  tests/fixtures/prompt_surface/tools/manage_connections.json
e97afc5ad07fcf267f9c200710b512bbbc539e8e7e046f622190b5ea09bdee37  tests/fixtures/prompt_surface/tools/memory.json
391d424d1dd7ae0e44e353a58e77552f83bf47284df5a23244fc21471597e20e  tests/fixtures/prompt_surface/tools/patch.cli.gpt.json
c6c3637c4009b5efaa8dfdf206cd5e250a7f96d8eb6f7935ca088b6aacb7a27e  tests/fixtures/prompt_surface/tools/patch.json
79159bd19fafabf75079921d35dd08a6d8e1b772c09203ddae57da3b503cc81e  tests/fixtures/prompt_surface/tools/react_to_message.json
95c260d8ea3d56533164a89cd9f7f54e46bf900d33fa4212078246b5abe3fc8d  tests/fixtures/prompt_surface/tools/read_file.json
c1265ade9764378439093f0457e2bc8b5b316443000e0575077b32d5f921b1d8  tests/fixtures/prompt_surface/tools/search_files.json
5d6e7642365f354b4ee5b41aaa69fdf68bec4cc4fa4ccbc04454823626bd582e  tests/fixtures/prompt_surface/tools/skill_manage.json
c0d00b12f214d0ca5ebcf7249f96d8523985600ea8784942f1d42f7ca62c0452  tests/fixtures/prompt_surface/tools/skills_list.json
3b599a6f19cfec53f93e4a602231ab6406f92eaf104ee983cf6c9e58edf8e298  tests/fixtures/prompt_surface/tools/skill_view.json
ec11a1014af36d295438ab5e694edae68fd5862baccec1369f2f081886f1a796  tests/fixtures/prompt_surface/tools/terminal.json
730a06971d052d1f069b84946262c80fcd4d8edd474a53943a6dc47427f7cf50  tests/fixtures/prompt_surface/tools/text_to_speech.json
98c1f98e773e1cfc60b3565d1f33557ec93966ffc81c84c8cabe854da70e065e  tests/fixtures/prompt_surface/tools/tool_call.json
5ad5db7f4ca73598a6fdb139ffb652d1883959155e165da31a1c03622f1e9517  tests/fixtures/prompt_surface/tools/tool_describe.json
50fcf75c1cfba2c6903434eacd4e33c977bbcef60f283f66e733a27c01168ec5  tests/fixtures/prompt_surface/tools/tool_search.desktop.claude.json
e5113c387050283d525c6dd6ed3cac81435a57db30e17fe862637f63dea68643  tests/fixtures/prompt_surface/tools/tool_search.json
869e830b5560a002ff20f782557ab70584fe31cd6ff00063d6c26edea8e0d917  tests/fixtures/prompt_surface/tools/vision_analyze.json
e5e9df35f136a1e3b00377c53ee6bedcdc1fe074598f0a8856aa60b827fcae44  tests/fixtures/prompt_surface/tools/web_extract.json
2555403b770bc554c54812db9e0f8ec6edf409be98060ba4b46d454b12455ede  tests/fixtures/prompt_surface/tools/web_search.json
f0a57a062afcbdd80ea8af0b38a26c550e0091ff3ec9936e1cb8976225f0814c  tests/fixtures/prompt_surface/tools/write_file.json
18d687ef29ed2818a90c96949c2c9556dd5721e2ec6afa64ea9cf16c91f7e089  tests/fixtures/provider_wire_snapshot.json
23aa3ada30350cc2fb32619e28ebefaeea29a0618fd1c194c0d181154db6a73a  tests/fixtures/resolution_allowlist.json
5cd4d01f70348fd188342b7f06145e888f8d3d4d22f44db8d604db819e5930da  tests/fixtures/room_link_protocol_v2.json
05ebdc61124bd53f48abfa7dd1be0653ebec20eebf182e347c6f08cd80489300  tests/fixtures/session-resume-active-turn.json
42ecc00ba3639f49de8324b8ff481d9ab7789975e0a5b4e488e4cda6f67c7e25  tests/fixtures/spark_failing_turn_shape.json
b16d125774b2e5358246a07628359a00e7e493c7b8b2dfc3b8206ab8a1876a85  tests/fixtures/update_marker_corpus.json
57f0fb7fe9b03dd24a5f1f8faae1f98bae7be0f542cecfbab8fba5f532eccc2a  tests/gateway/fixtures/agent_persistence_worker.py
8f422fdc839f1a4190d8a8f0850cc51184c3c0444037a22ff7ff67a575bca8f8  tests/gateway/fixtures/ancillary_reads_peer.py
d2e7f77acc647e5b996cefe8a8fc7e66031dcb236277ecb53cc00831e58eb5f8  tests/gateway/fixtures/api_authority_peer.py
edbc95c6ac9cd67e28023cd0df8e4d6d88cd27509c082c4b254eecf0c0aa7b5d  tests/gateway/fixtures/api_daemon_witness.py
db2c81f4157ebbdf09283b9e05fc80b835dea37e27969c5b8b8f8b49b10bb962  tests/gateway/fixtures/api_recovery_daemon.py
a186fcfa2b1706a296222de85fc3879b83be11bdaa3db404c80621ca3b24e2df  tests/gateway/fixtures/api_usage_peer.py
ebc489de3e962b7b669d398b8a3f9602a39ba0bbfeffca583eb1f61356dffe8a  tests/gateway/fixtures/authority_clarify_lock_peer.py
c89e9a15aa4e75708fa792daaf745a983a76a5e36fdc5b6c62b04a4bd65bb616  tests/gateway/fixtures/authority_clarify_peer.py
119b7dcba7c27207193e3b0ee8bdfb7535ce066b47a29c6c8343dae6b0c33206  tests/gateway/fixtures/authority_controls_peer.py
8aa221466ea0147f20c4850dbc5b4fe34bcd78029eb7b3cea7cf400b2cda22a3  tests/gateway/fixtures/authority_events_peer.py
6c45e4328d265b954cc899b31b565187dad70ee528afe630baed35e3f73c8bd7  tests/gateway/fixtures/authority_stream_peer.py
9a8844d29d10889a9576d0f0646bf0faf8db58231e609a5124f395469f0f77b7  tests/gateway/fixtures/automation_peer.py
31bb9f95643ef0321eb2d7d94fa7b68934da0bc1e612490f03388cb7dd5934bc  tests/gateway/fixtures/bot_authority_peer.py
cf0ea72785810512498aba256697d064e515ae935cba699692fe89f22b332cfe  tests/gateway/fixtures/browser_scope_peer.py
d1a986f4e2d3dd943927a4f13068223b8314fed71067acb0aeaec3e186d10f0a  tests/gateway/fixtures/cli_launch_policy_probe.py
d76a541a40c90a306d17a17d3e1d144af885acccbff09f69177ecd919e63c441  tests/gateway/fixtures/cli_plugin_free_startup.py
f251a4f1d70c9ea76238b03a144b06565449b2d0482e02d5742040c14ebe323f  tests/gateway/fixtures/compression_persistence_worker.py
9cd1efbfcf4e4a38ce6be6a659c01cf57e9582935cccab5f6cc8dd92e48503ce  tests/gateway/fixtures/config_policy_recovery_probe.py
dbd556cd49f460e7dfec6aa7c1f8f4853f545815d9fc2d9ff077a4b54d2a3d48  tests/gateway/fixtures/control_boundaries.py
57eef927149330bf82235fa2cffd56758c4c196ba9f93a5e8496ade3bdbb6b01  tests/gateway/fixtures/desktop_process_verbs_peer.py
7f5459e7dc341d5bf864bb46d6e9e92b3c1206b1364f00d651a2161dff307cdd  tests/gateway/fixtures/estop_interactive_peer.py
2480247e6e791f0133faacad78cd35cfc34ccce6741f1fca9691ef1dfba62d94  tests/gateway/fixtures/execution_frames_capture.py
eccb871bab0fc01ee9d394bf22fe94ebe7a0276645d5c41da34dfda17e7ccfc5  tests/gateway/fixtures/hosted_auth_probe.py
990d1f4579256081f21a271de551fa7e4b53da5c07f099c7aed1161d519ae9d2  tests/gateway/fixtures/kanban_owner_probe.py
12783737a96f6676ce8524bf69ddc984dcb34dc978a9531ff8433849e7dc0273  tests/gateway/fixtures/kanban_recovery_probe.py
2be68fd181a3827ec9bb7626ff2eedb86a2227f84d5431847a92bda106421455  tests/gateway/fixtures/ledger_tool_worker.py
2d0f88b0ebf6f57ab33eb9b905670259666c3d52dd47b44a67baa305701b4795  tests/gateway/fixtures/legacy_bot_mailbox.py
4617ca973f78a1b362a7d2c374a9257df90aac0c0b947b6f227e709935cc0905  tests/gateway/fixtures/legacy_migration_probe.py
a62e20642ce6f1d807f9820110c17ce7c4e37432d36ad290fb06fe7f85f521fd  tests/gateway/fixtures/lifecycle_persistence_worker.py
fe99535c542acd3774fe5f6378a98c15fedce82d405655477f34c71b9e4a49c1  tests/gateway/fixtures/local_automation_daemon.py
a82a4060feedb2fc980cf5c2ad1c617a921f71098e84ec1fa0213d2c579f1c73  tests/gateway/fixtures/local_automation_peer.py
397111f03c9b01098b749b5e3fdc0c73cb14551bb175ec1f705d588781d4dc91  tests/gateway/fixtures/local_lineage_daemon.py
b6dccdca225286a87966f5fe46f92789d797b18ffc5463161f4be4d6e867d781  tests/gateway/fixtures/local_lineage_probe.py
78aeaad7a873a347097e33dbfd2b893421264f4e8be0d95703b7d49a48331d21  tests/gateway/fixtures/local_recovery_daemon.py
db8e96453b8977ced214796d3f0c140a0fea030134a481e2899d397f3ebe280f  tests/gateway/fixtures/local_recovery_probe.py
94fca9d4f46b3c8c82a8add0bda96464816b8dc06b3f4674299abaf410091cc8  tests/gateway/fixtures/local_session_peer.py
27ebec1134a99bd8048a98cdf410dfa9db87d17a70096a9b78b1fc7ac38d5249  tests/gateway/fixtures/local_status_notice_peer.py
28b06bcf0064ffdd3f8e6bc27116f6406b700ed240cab364451c075ce12a1bc7  tests/gateway/fixtures/native_ingress_media_peer.py
538bfa41014399febead0604dcc1a6169305def11078004081739ae80528819d  tests/gateway/fixtures/native_ingress_trust_multiplex.py
9e8839bc9e6a1af1ce5349465286a94d40fa1cfe8166be38ed72196ea40769d0  tests/gateway/fixtures/native_ingress_trust_peer.py
92473a6afa9231a22fc1e84821691ddad7377b5d95dcc982360eae299b2eb082  tests/gateway/fixtures/native_reply_crash_daemon.py
7374a65fc82af7d0a1227b49ad9b0d002ed14826eee6793cfd4fb0f3d1f5b19c  tests/gateway/fixtures/native_role_fences.py
6db52686664cecf5761660d8521b429ba765312d754f36541712a0b302836a47  tests/gateway/fixtures/native_role_peer.py
393e6032bc628b9feebeb1ce6f98f5ef3f7b2ada702409bce74fc3d931bf2f45  tests/gateway/fixtures/native_telegram_recovery_daemon.py
7d6aede03a443c61d9d3600f30245f60b6569ca38e32ed5a6de6762d1660bf3b  tests/gateway/fixtures/operator_cross_surface_peer.py
320a2d00426f9cc4978ecdcaaf15f7cd06e727a6187932f50b18d3a489db5835  tests/gateway/fixtures/owner_process.py
5bbd229636877a2bf4ea6c778dbbef09067a1addfa7aa6487285f5f1fbd85902  tests/gateway/fixtures/persistence_worker.py
05186bbb05b6e1ca08d147df6340dc35da9e45df619e7c7de71e2fba1066fb9d  tests/gateway/fixtures/plugin_mcp_daemon.py
f9b40fc90670c6ca99f0fc1a35dfdd15ac2f59b69ac646a5be38c670b6481b1f  tests/gateway/fixtures/process_scope_peer.py
5eadb35d0065b8e9726e7c031169de8daa006bc5edfd826ea0844d87b39fdc34  tests/gateway/fixtures/replay_gap_owner.py
ce073e06d1dec25e52ad9bdac84faff9716fde5311b362ac5dcd48a6c9a04dbc  tests/gateway/fixtures/rotation_persistence_worker.py
e73e5a073eb74a4c8a2b38ca83ebba452e9e1cb1bbcd36b8cbb3107792ce3aa2  tests/gateway/fixtures/session_policy_peer.py
4a6481b0b8cc1a4b1b098db375c01fc182a525fb0b2f655460f4bbe619bc8209  tests/gateway/fixtures/shared_authority_peer.py
e64a4d2c51d4bb79aad4368f3af5fbe5cd95b9b29fcd6a83d3315b93fad03aa3  tests/gateway/fixtures/shared_authority_recovery.py
e44a43909e5fe77aa041a503fcb15a1af876a4da24bb7dffb5a2f5d4e7e1157a  tests/gateway/fixtures/shell_exec_peer.py
c30dd9b2a8ac66111c72526ceb41472cc2a213ac321003badb3119b2c29fda9a  tests/gateway/fixtures/stack_dump_daemon.py
00fc05f9abb9e1ae7b99b957708a3278b46c246e8713fe0512161e48af658c7b  tests/gateway/fixtures/staged_file_attach_peer.py
f76c3cee426a939a93cd152c5cfd06aceb5d6bf54d2ec6e2a69e287ffe05c17d  tests/gateway/fixtures/subagent_controls_peer.py
6d71451e3a4147243ab4eb92e36f49677a15e78e4f239f851cb3f42c08120956  tests/gateway/fixtures/terminal_commit_daemon.py
f059c3593be209bcc6c3fc07084007b0605463a83ae2218ee3cfe2bc7b77c1f8  tests/gateway/fixtures/trampoline_daemon.py
9212094c09080bb41ac81db614faf27e410e8fa1e091438055a94f743d2dc8bc  tests/gateway/fixtures/tui_desktop_routes_peer.py
72e33f048986630f2363f11d45a4cd0c49d5e2410a051a379480199c74838479  tests/gateway/fixtures/webapp_fallback_peer.py
79d4aa18e064e159c76cdc2fdb0aa5999cde21434ad9b3fba4a0719182bf92ed  tests/gateway/fixtures/webapp_gated_sign_out_peer.py
94960bed0c8833df565ad971d6eaf97aff0f2bdeeaee9b33bba63064de2abd5c  tests/gateway/fixtures/webapp_listener_peer.py
6d057f5ad2cf34f097fe98043c0c1bdf5b1515bfee576750103c40eb315cfbb3  tests/gateway/fixtures/webhook_route_authority.py
58be51dc7fbc330b6a802689a5f0ef917cf53701d16659560f28bc60ea4ba93b  tests/hermes_cli/fixtures/plugin_compat_legacy/__init__.py
bce46af1fae0471b3702f4dbe91121b39799712d66609cbeef945977fff6226f  tests/hermes_cli/fixtures/plugin_compat_legacy/plugin.yaml
0832bc2d4d7ef9c4cb3ad5d62cb684df11052e5008339db461f3a373bc61960d  tests/plugins/fixtures/kanban_touch_drag_probe.js
```
