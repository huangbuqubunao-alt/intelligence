import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ExistingSourceForm } from "./App";
import { UiLanguageProvider } from "./uiLanguage";
const response = (value: object) => Promise.resolve({ ok: true, json: async () => value });
beforeEach(() => localStorage.setItem("yia.ui-language", "en"));
afterEach(() => vi.unstubAllGlobals());
test("advanced source configuration preserves the bounded V1 controls", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string) => {
      if (input.endsWith("/sources")) return response({ sources: [] });
      return response({});
    }),
  );
  render(<UiLanguageProvider><ExistingSourceForm onClose={vi.fn()} onSaved={vi.fn()} /></UiLanguageProvider>);
  fireEvent.click(screen.getByText("Advanced source configuration"));

  expect(await screen.findByRole("heading", { name: "Add a Source" }))
    .toBeTruthy();
  expect(screen.getByLabelText("Source URL")).toBeTruthy();
  expect(screen.getByLabelText("Monitor this Source")).toBeTruthy();
  expect(screen.getByLabelText("Automatic schedule")).toBeTruthy();
  expect(screen.getByLabelText("Initial history")).toBeTruthy();
  expect(screen.getByLabelText("Per-run limit")).toBeTruthy();
  expect((screen.getByLabelText("Focus preference") as HTMLSelectElement).value).toBe("INHERIT");
  for (const label of ["Focus preference", "Ignore preference", "Style preference"]) fireEvent.change(screen.getByLabelText(label), { target: { value: "OVERRIDE" } });
  expect(screen.getByLabelText("Focus")).toBeTruthy();
  expect(screen.getByLabelText("Ignore")).toBeTruthy();
  expect(screen.getByLabelText("Distillation style")).toBeTruthy();
  expect(
    screen.getByText(
      /recent existing videos are considered when this Following is first added/i,
    ),
  ).toBeTruthy();
  expect(
    screen.getByText(
      /maximum number of new videos processed in one check/i,
    ),
  ).toBeTruthy();
  expect(
    Array.from(
      (screen.getByLabelText("Initial history") as HTMLSelectElement).options,
    ).map((option) => option.value),
  ).toEqual(["0", "1", "3", "5", "10"]);
  expect(
    Array.from(
      (screen.getByLabelText("Per-run limit") as HTMLSelectElement).options,
    ).map((option) => option.value),
  ).toEqual(["1", "3", "5", "10"]);
  expect(
    Array.from(
      (screen.getByLabelText("Distillation style") as HTMLSelectElement)
        .options,
    ).map((option) => option.value),
  ).toEqual([
    "BALANCED",
    "TECHNICAL_DETAIL_FIRST",
    "PRODUCT_CASE_FIRST",
    "TREND_OPINION_FIRST",
  ]);
  expect(screen.getByText(/Add at least one focus word/)).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Source URL"), {
    target: { value: "https://youtube.test/new" },
  });
  fireEvent.click(screen.getAllByRole("button", { name: "Add Source" }).at(-1)!);
  expect(screen.getAllByText(/Add at least one focus word/).length).toBeGreaterThan(1);
  expect(fetch).not.toHaveBeenCalledWith(
    "/api/v1/sources",
    expect.objectContaining({ method: "POST" }),
  );
});

test("Source setup writes only through the existing Source, policy, and schedule commands", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string, init?: RequestInit) => {
      if (input.endsWith("/sources") && init?.method === "POST") {
        return response({
          source: {
            source_id: "source-new",
            canonical_url: "https://youtube.test/new",
            enabled: true,
            processing_policy: "STANDARD_INTELLIGENCE",
            display_name: null,
            last_error: null,
          },
        });
      }
      if (input.endsWith("/sources/source-new/policy")) {
        return response({ policy: {}, applied_source_policy_revision_id: "r1", current_source_policy_revision_id: "r1", historical_replay: false });
      }
      if (
        input.endsWith("/sources/source-new") && init?.method === "PATCH"
      ) return response({ source: {} });
      if (input.endsWith("/automation")) return response({ schedule: {} });
      if (input.endsWith("/sources")) return response({ sources: [] });
      return response({});
    }),
  );
  render(<UiLanguageProvider><ExistingSourceForm onClose={vi.fn()} onSaved={vi.fn()} /></UiLanguageProvider>);
  fireEvent.click(screen.getByText("Advanced source configuration"));
  fireEvent.change(screen.getByLabelText("Source URL"), {
    target: { value: "https://youtube.test/new" },
  });
  fireEvent.click(screen.getByLabelText("Monitor this Source"));
  fireEvent.change(screen.getByLabelText("Initial history"), {
    target: { value: "3" },
  });
  fireEvent.change(screen.getByLabelText("Per-run limit"), {
    target: { value: "10" },
  });
  for (const label of ["Focus preference", "Ignore preference", "Style preference"]) fireEvent.change(screen.getByLabelText(label), { target: { value: "OVERRIDE" } });
  fireEvent.change(screen.getByLabelText("Focus"), {
    target: { value: "product, AI" },
  });
  fireEvent.change(screen.getByLabelText("Ignore"), {
    target: { value: "rough" },
  });
  fireEvent.change(screen.getByLabelText("Distillation style"), {
    target: { value: "PRODUCT_CASE_FIRST" },
  });
  fireEvent.change(screen.getByLabelText("Automatic schedule"), {
    target: { value: "WEEKLY" },
  });
  fireEvent.click(
    screen.getAllByRole("button", { name: "Add Source" }).at(-1)!,
  );
  await waitFor(() =>
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/sources",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          url: "https://youtube.test/new",
          processing_policy: "STANDARD_INTELLIGENCE",
        }),
      }),
    )
  );
  await waitFor(() => expect(fetch).toHaveBeenCalledWith("/api/v1/automation", expect.objectContaining({ method: "POST" })));
  expect(fetch).toHaveBeenCalledWith(
    "/api/v1/sources/source-new",
    expect.objectContaining({
      method: "PATCH",
      body: JSON.stringify({
        enabled: false,
        processing_policy: "STANDARD_INTELLIGENCE",
      }),
    }),
  );
  expect(fetch).toHaveBeenCalledWith(
    "/api/v1/sources/source-new/policy",
    expect.objectContaining({
      method: "PUT",
      body: expect.stringContaining('"initial_history_count":3'),
    }),
  );
  expect(fetch).toHaveBeenCalledWith(
    "/api/v1/automation",
    expect.objectContaining({
      method: "POST",
      body: expect.stringContaining('"target_type":"SOURCE_CHECK"'),
    }),
  );
});
