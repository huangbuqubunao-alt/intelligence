# 02｜Wave 5 迭代演进与验证日志（Iteration Log）

- **分支**：`antigravity/autonomous-product-evolution-wave5-20261127`
- **堆叠基线（Wave 4 PR #55）**：`1ed93e67281ebf59044c53c67e553f5934bf6f4b` (14/14 CI green)
- **回退约定**：Iter 24–29 均为单一产品目标的原子提交；任一需求均可单次 `git revert <sha>` 独立撤回，或整批回退至 Wave 4 (`1ed93e67`) / Wave 3 (`ecb843ea`) / Wave 2 (`edd0b0b9`) / Wave 1 (`088554c4`) / `main` (`f7b97134`)。

---

## Iteration 24 (`EVO-W5-01`) — `#Content` Saved Smart Filter Views ("自定义常用视图")

- **解决的用户问题**：高频研究者在 `#Content` 常复用固定的多维筛选组合（如「必看长视频 + #核心结论」或特定频道+关键词），此前每次进入需重复逐项筛选，工作流无法沉淀。
- **核心改动**：
  1. 新增 [savedViews.ts](../../../frontend/src/workspace/savedViews.ts)：实现 `SavedContentView` 6 维组合条件持久化（`yia.content_saved_views.v1`、上限 8 条、相同条件自动去重更新、合法字面量规范校验）、默认命名生成器 `suggestSavedViewName` 与跨组件事件同步 `SAVED_VIEWS_CHANGED_EVENT`。
  2. [App.tsx](../../../frontend/src/workspace/App.tsx) & [styles.css](../../../frontend/src/workspace/styles.css)：有激活筛选时出现「保存视图」按钮与内联命名表单 `.content-save-view-popover`；存在已存视图时呈现 `.content-saved-views-strip`（「常用视图：」），采用双独立 `<button>` 胶囊（选择与删除绝不嵌套）一键还原 6 维筛选状态。
- **自动化验证**：
  - 新增 [EvolutionIter24.test.tsx](../../../frontend/src/workspace/EvolutionIter24.test.tsx)（2 passed，覆盖名称建议、同条件去重、`#Content` 多维保存/重置/一键恢复与兄弟删除键移除）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`951ms` (`assets/index-DJD-T-1I.js` / `assets/index-DxNL4ko4.css`)；Vitest：**82/82 files, 1328/1328 passed**。
- **Chromium 实机验证（`127.0.0.1:8799/#Content`）**：
  - 确认加载新资源 `index-DJD-T-1I.js` & `index-DxNL4ko4.css`（HTTP `200`）；保存「周度必看精选」后重置筛选再点击恢复过滤均精确生效，删除胶囊 cleanly 移除；Dark / Light / `390x844` 移动端（`mobileOverflow: false`）；**0 console/page/network 错误**。
  - 实机截图归档：[Saved Views Dark](./screenshots/iter-24/step_1_iter24_saved_views_dark.png)、[Saved Views Light](./screenshots/iter-24/step_2_iter24_saved_views_light.png)、[Saved Views Mobile](./screenshots/iter-24/step_3_iter24_saved_views_mobile.png)。
