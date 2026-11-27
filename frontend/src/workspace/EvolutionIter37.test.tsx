import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import {
  deletePersonalTag,
  readPersonalNote,
  renamePersonalTag,
  savePersonalNote,
} from "./personalNotes";

function okJson(payload: unknown): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("Iteration 37 (EVO-W7-02): #Topics personal tag governance (rename, merge & delete)", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.onboarding_completed.v1", "1");
    localStorage.setItem("yia.ui-language", "zh-CN");
    location.hash = "#Topics";
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    localStorage.clear();
    location.hash = "";
  });

  it("renamePersonalTag merges synonymous tags cleanly without losing note text", () => {
    savePersonalNote("v1", { text: "关于 Agent 状态机的关键笔记", tags: ["Agents", "架构"] });
    savePersonalNote("v2", { text: "保留两份思考", tags: ["Agent", "Agents"] });

    const res = renamePersonalTag("Agents", "Agent");
    expect(res.targetTag).toBe("Agent");
    expect(res.affectedCount).toBe(2);

    expect(readPersonalNote("v1")?.tags).toEqual(["Agent", "架构"]);
    expect(readPersonalNote("v1")?.text).toBe("关于 Agent 状态机的关键笔记");
    expect(readPersonalNote("v2")?.tags).toEqual(["Agent"]);
    expect(readPersonalNote("v2")?.text).toBe("保留两份思考");
  });

  it("deletePersonalTag preserves note text when text exists and removes tag-only shell entries", () => {
    savePersonalNote("vText", { text: "有正文的笔记绝不删", tags: ["临时标签"] });
    savePersonalNote("vTagOnly", { text: "", tags: ["临时标签"] });

    const res = deletePersonalTag("临时标签");
    expect(res.affectedCount).toBe(2);

    expect(readPersonalNote("vText")?.text).toBe("有正文的笔记绝不删");
    expect(readPersonalNote("vText")?.tags).toEqual([]);
    expect(readPersonalNote("vTagOnly")).toBeNull();
  });

  it("exposes inline tag rename/merge and delete controls inside #Topics", async () => {
    savePersonalNote("v1", { text: "个人深度批注内容", tags: ["Agents", "实战"] });
    savePersonalNote("v2", { text: "另一篇批注", tags: ["Agent"] });

    vi.stubGlobal("fetch", (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/system")) {
        return okJson({ health: "ready", edition: "LOCAL" });
      }
      if (url.includes("/api/v1/topics")) {
        return okJson({ topics: [] });
      }
      return okJson({});
    });

    render(<App />);

    const manageBtn = await screen.findByRole("button", { name: "管理标签" });
    fireEvent.click(manageBtn);

    const renameInput = await screen.findByLabelText("重命名标签 Agents");
    fireEvent.change(renameInput, { target: { value: "Agent" } });

    const renameBtns = screen.getAllByRole("button", { name: "重命名 / 合并" });
    const activeRenameBtn = renameBtns.find((btn) => !(btn as HTMLButtonElement).disabled)!;
    fireEvent.click(activeRenameBtn);

    await waitFor(() => {
      expect(screen.getByText(/已将 #Agents 重命名\/合并为 #Agent（更新 1 篇）/)).toBeTruthy();
    });
    expect(readPersonalNote("v1")?.tags).toEqual(["Agent", "实战"]);

    fireEvent.click(screen.getByLabelText("删除标签 实战"));
    await waitFor(() => {
      expect(screen.getByText(/已从 1 篇内容移除标签 #实战（批注正文已保留）/)).toBeTruthy();
    });
    expect(readPersonalNote("v1")?.text).toBe("个人深度批注内容");
    expect(readPersonalNote("v1")?.tags).toEqual(["Agent"]);
  });
});
