import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { completeOnboarding } from "./Onboarding";

function okJson(payload: unknown): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function baseSettingsResponse() {
  return {
    general: {
      timezone: "Asia/Shanghai",
      output_language: "zh-CN",
      output_language_source: "EXPLICIT",
      output_language_updated_at: "2026-11-17T00:00:00Z",
    },
    providers: [
      {
        provider: "Local",
        model: "qwen3.5:9b",
        adapter_available: true,
        qualification_status: "QUALIFIED",
        authorized: true,
        production_eligible: true,
        scope: "SCORING_SUMMARY_ONLY",
        reason: "READY",
      },
    ],
    runtime_local_model: {
      model: "qwen3.5:9b",
      status: "READY",
      installed: true,
      digest_valid: true,
    },
    cloud_credential: { configured: false, source: "NONE" },
    model_preference: { desired_provider: null, desired_model: null },
  };
}

function mockSettingsFetch(
  policyPayload: unknown,
  onPut?: (body: { command_id: string; focus_rules: string[]; ignore_rules: string[]; distillation_style: string }) => Promise<Response>,
) {
  return vi.fn((input: string | URL | Request, init?: RequestInit) => {
    const path = String(input);
    if (path.endsWith("/settings/source-policy")) {
      if (init?.method === "PUT" && onPut) {
        return onPut(JSON.parse(String(init.body)));
      }
      return okJson({ policy: policyPayload });
    }
    if (path.endsWith("/settings")) return okJson(baseSettingsResponse());
    if (path.endsWith("/settings/preferences")) return okJson({ active: [], history: [] });
    if (path.endsWith("/settings/resource-usage")) return okJson({ usage: [] });
    if (path.endsWith("/settings/local-models")) return okJson({ connection: "REACHABLE", models: [] });
    if (path.endsWith("/settings/local-intelligence")) return okJson({ local_intelligence: null });
    if (path.endsWith("/local/transcription/status")) return okJson({ status: { state: "READY" } });
    if (path.endsWith("/backup-restore/status")) {
      return okJson({ status: { ready: true, reasons: [], message: "Ready", restore_pending: false, last_restore: null } });
    }
    if (path.endsWith("/knowledge-delta")) return okJson({ knowledge_delta: { generated_at: "2026-11-17T00:00:00Z", window_days: 7, counts: {}, items: [] } });
    return okJson({});
  });
}

describe("GlobalInterests UX: Cancel/Escape & passive lock retry", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
    completeOnboarding();
    location.hash = "#Settings";
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows focus/ignore/style in read mode and supports Cancel button + Escape key to discard unsaved drafts without calling PUT", async () => {
    const puts: unknown[] = [];
    const savedPolicy = {
      initial_history_count: 5,
      per_run_max_new_videos: 5,
      focus_rules: ["AI Agent"],
      ignore_rules: ["娱乐八卦"],
      distillation_style: "PRODUCT_CASE_FIRST",
    };

    vi.stubGlobal(
      "fetch",
      mockSettingsFetch(savedPolicy, body => {
        puts.push(body);
        return okJson({ policy: savedPolicy });
      }),
    );

    render(<App />);

    const editBtn = await screen.findByRole("button", { name: "编辑兴趣" });
    const panel = editBtn.closest("section")!;
    expect(panel.textContent).toContain("AI Agent");
    expect(panel.textContent).toContain("娱乐八卦");
    expect(panel.textContent).toContain("产品案例优先");

    // Enter edit mode, mutate draft, then click Cancel (取消)
    fireEvent.click(editBtn);
    const focusInput = await within(panel).findByLabelText("我重点关注");
    fireEvent.change(focusInput, { target: { value: "临时未保存草稿" } });

    const cancelBtn = within(panel).getByRole("button", { name: "取消" });
    fireEvent.click(cancelBtn);

    expect(within(panel).queryByRole("button", { name: "保存偏好" })).toBeNull();
    expect(within(panel).getByRole("button", { name: "编辑兴趣" })).toBeTruthy();
    expect(puts).toHaveLength(0);

    // Reopen edit mode: draft was cleanly reset back to saved policy, and Escape also cancels
    fireEvent.click(within(panel).getByRole("button", { name: "编辑兴趣" }));
    const reopenedFocus = (await within(panel).findByLabelText("我重点关注")) as HTMLTextAreaElement;
    expect(reopenedFocus.value).toBe("AI Agent");
    fireEvent.change(reopenedFocus, { target: { value: "第二次草稿" } });
    fireEvent.keyDown(reopenedFocus, { key: "Escape" });

    expect(within(panel).queryByRole("button", { name: "保存偏好" })).toBeNull();
    expect(puts).toHaveLength(0);
  });

  it("retries transient 409 CONFIGURATION_APPLYING lock conflict with the same idempotent command_id and confirms save", async () => {
    const putPayloads: { command_id: string; focus_rules: string[] }[] = [];
    const savedPolicy = {
      initial_history_count: 5,
      per_run_max_new_videos: 5,
      focus_rules: ["AI Agent", "一人公司"],
      ignore_rules: [],
      distillation_style: "BALANCED",
    };

    vi.stubGlobal(
      "fetch",
      mockSettingsFetch(savedPolicy, body => {
        putPayloads.push(body);
        if (putPayloads.length === 1) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                error: {
                  code: "CONFIGURATION_APPLYING",
                  message: "Local model settings are applying. Wait for the local service to reconnect.",
                },
              }),
              { status: 409, headers: { "Content-Type": "application/json" } },
            ),
          );
        }
        return okJson({ policy: savedPolicy });
      }),
    );

    render(<App />);
    const editBtn = await screen.findByRole("button", { name: "编辑兴趣" });
    const panel = editBtn.closest("section")!;
    fireEvent.click(editBtn);

    // Click save without changing any rules (exact user QA scenario)
    fireEvent.click(await within(panel).findByRole("button", { name: "保存偏好" }));

    await waitFor(
      () => {
        expect(putPayloads).toHaveLength(2);
        expect(within(panel).getByRole("button", { name: "编辑兴趣" })).toBeTruthy();
      },
      { timeout: 3500 },
    );

    expect(putPayloads[0].command_id).toBeTruthy();
    expect(putPayloads[1].command_id).toBe(putPayloads[0].command_id);
    expect(within(panel).queryByRole("alert")).toBeNull();
    expect(panel.textContent).toContain("偏好已保存。");
  });
});
