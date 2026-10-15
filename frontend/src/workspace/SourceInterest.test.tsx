import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CreatorFollowingDetail } from "./CreatorFollowing";
import { UiLanguageProvider } from "./uiLanguage";

const policy = { source_id: "channel-a", source_policy_revision_id: null as string | null, initial_history_count: 5, per_run_max_new_videos: 5, focus_rules: ["robotics"], ignore_rules: [], distillation_style: "BALANCED" };
const detail = (id = "channel-a", changes = {}) => ({ source: { source_id: id, provider: "YOUTUBE", display_name: "Channel", canonical_url: "https://www.youtube.com/@example", enabled: true, last_checked_at: null, last_success_at: null, tracking: { health: "HEALTHY", coverage: "COMPLETE", update_count: 0, pending_count: 0 } }, recent_videos: [], source_runs: [], policy: { ...policy, source_id:id }, policy_modes: { focus:"INHERIT", ignore:"INHERIT", style:"INHERIT" }, ...changes });
const response = (value: unknown, ok = true) => ({ ok, status: ok ? 200 : 409, json: async () => value });
const view = (id = "channel-a") => <UiLanguageProvider><CreatorFollowingDetail id={id} capability={{ known:true, capability:{ available:true, code:"AVAILABLE" } }} onClose={vi.fn()} onRefresh={vi.fn()} /></UiLanguageProvider>;
const save = () => screen.getByRole("button", { name:"Save interests" }) as HTMLButtonElement;
async function edit() { fireEvent.click(await screen.findByRole("button", { name:"Edit interests" })); await screen.findByLabelText("Focus preference"); }
beforeEach(() => localStorage.setItem("yia.ui-language", "en"));
afterEach(() => { vi.unstubAllGlobals(); localStorage.clear(); });

it("saves only one interest command with captured null expected and keeps all other settings untouched", async () => {
  const fetcher = vi.fn(async (_url: string, init: RequestInit) => init.method === "PUT" ? response({ applied_source_policy_revision_id:"r1", current_source_policy_revision_id:"r1", historical_replay:false }) : response(detail())); vi.stubGlobal("fetch",fetcher);
  render(view()); await edit();
  fireEvent.change(screen.getByLabelText("Focus preference"), { target:{ value:"OVERRIDE" } });
  fireEvent.change(screen.getByLabelText("Focus"), { target:{ value:"my draft" } });
  fireEvent.click(save()); await screen.findByText("Interests saved.");
  const writes = fetcher.mock.calls.filter(([, init]) => init.method === "PUT");
  expect(writes).toHaveLength(1);
  expect(writes[0][0]).toBe("/api/v1/sources/channel-a/interests");
  const body = JSON.parse(writes[0][1].body as string);
  expect(body).toEqual({ command_id:expect.any(String), expected_source_policy_revision_id:null, focus_mode:"OVERRIDE", focus_rules:["my draft"], ignore_mode:"INHERIT", ignore_rules:[], distillation_style_mode:"INHERIT", distillation_style:null });
  expect(fetcher.mock.calls.every(([,init]) => !init.method || init.method === "GET" || init.method === "PUT")).toBe(true);
});
it("preserves conflict draft, only explicitly reloads GET, and sends a fresh command after rebasing", async () => {
  let version:string|null = null;
  const fetcher = vi.fn(async (_url:string, init:RequestInit) => {
    if (init.method === "PUT") { version="r1"; return response({ error:{ code:"CONFLICT", message:"conflict" } }, false); }
    return response(detail("channel-a", { policy:{ ...policy, source_policy_revision_id:version, focus_rules:["server"] } }));
  }); vi.stubGlobal("fetch",fetcher); render(view()); await edit();
  fireEvent.change(screen.getByLabelText("Focus preference"), { target:{value:"OVERRIDE"} });
  fireEvent.change(screen.getByLabelText("Focus"), {target:{value:"unsaved draft"}});
  fireEvent.click(save()); await screen.findByText("Interests changed elsewhere. Your draft is preserved. Reload the current version before saving again.");
  expect((screen.getByLabelText("Focus") as HTMLInputElement).value).toBe("unsaved draft"); expect(save().disabled).toBe(true);
  expect(fetcher.mock.calls.filter(([,i])=>i.method==="PUT")).toHaveLength(1);
  const before=fetcher.mock.calls.length; fireEvent.click(screen.getByRole("button",{name:"Reload current interests"})); await waitFor(()=>expect(save().disabled).toBe(false));
  expect(fetcher.mock.calls.length).toBe(before+1); expect((screen.getByLabelText("Focus") as HTMLInputElement).value).toBe("unsaved draft");
  fireEvent.click(save()); await waitFor(()=>expect(fetcher.mock.calls.filter(([,i])=>i.method==="PUT")).toHaveLength(2));
  const bodies=fetcher.mock.calls.filter(([,i])=>i.method==="PUT").map(([,i])=>JSON.parse(i.body as string));
  expect(bodies[1].expected_source_policy_revision_id).toBe("r1"); expect(bodies[1].command_id).not.toBe(bodies[0].command_id);
});
it.each([{}, { policy:{...policy, source_policy_revision_id:undefined} }, {policy_modes:{focus:"UNKNOWN", ignore:"INHERIT", style:"INHERIT"}}, {policy:{...policy, distillation_style:"UNKNOWN"}}, {source:{...detail().source,source_id:"foreign"}}])("blocks invalid or unavailable interest snapshots and retries GET without saving", async changes => {
  let reads=0; const fetcher=vi.fn(async(_url:string, _init:RequestInit)=> { reads++; if(reads===1)return response(detail()); return response(Object.keys(changes).length ? detail("channel-a",changes) : {}); }); vi.stubGlobal("fetch",fetcher); render(view());
  fireEvent.click(await screen.findByRole("button",{name:"Edit interests"})); await screen.findByText("Interests could not be read. Retry before saving. Your draft is preserved.");
  expect(save().disabled).toBe(true); fireEvent.click(screen.getByRole("button",{name:"Reload current interests"})); await waitFor(()=>expect(reads).toBe(3));
  expect(fetcher.mock.calls.every(([,init]) => !init.method || init.method === "GET")).toBe(true);
});
it("does not report a historical replay as currently saved", async () => {
  vi.stubGlobal("fetch",vi.fn(async(_u:string,i:RequestInit)=>i.method==="PUT" ? response({applied_source_policy_revision_id:"old",current_source_policy_revision_id:"new",historical_replay:true}) : response(detail())));
  render(view()); await edit(); fireEvent.click(save()); await screen.findByText("This command was already applied, and newer interests exist. Your draft is preserved. Reload the current version."); expect(save().disabled).toBe(true);
});
it("ignores a late source read after switching Following", async()=>{
  let resolve!:(v:ReturnType<typeof response>)=>void;
  const fetcher=vi.fn((url:string)=>url.endsWith("channel-a") && fetcher.mock.calls.length>1 ? new Promise(r=>{resolve=r;}) : Promise.resolve(response(detail(url.endsWith("channel-b")?"channel-b":"channel-a")))); vi.stubGlobal("fetch",fetcher);
  const rendered=render(view()); fireEvent.click(await screen.findByRole("button",{name:"Edit interests"})); rendered.rerender(view("channel-b")); await act(async()=>resolve(response(detail())));
  expect(await screen.findByRole("button",{name:"Edit interests"})).toBeTruthy(); expect(screen.queryByLabelText("Focus preference")).toBeNull();
});

it("retains an early draft after a failed first policy read and successful explicit retry",async()=>{
 let calls=0; const fetcher=vi.fn(async()=>{ if(++calls===2)throw new TypeError("offline"); return response(detail()); });vi.stubGlobal("fetch",fetcher);render(view());
 fireEvent.click(await screen.findByRole("button",{name:"Edit interests"}));await screen.findByText("Interests could not be read. Retry before saving. Your draft is preserved.");
 fireEvent.change(screen.getByLabelText("Focus preference"),{target:{value:"OVERRIDE"}});fireEvent.change(screen.getByLabelText("Focus"),{target:{value:"early draft"}});
 fireEvent.click(screen.getByRole("button",{name:"Reload current interests"}));await waitFor(()=>expect(save().disabled).toBe(false));expect((screen.getByLabelText("Focus") as HTMLInputElement).value).toBe("early draft");
});
it("localizes the dedicated editor and cancels with Escape without any command",async()=>{
 localStorage.setItem("yia.ui-language","zh-CN");const fetcher=vi.fn(async(_u:string,_i:RequestInit)=>response(detail()));vi.stubGlobal("fetch",fetcher);render(view());
 fireEvent.click(await screen.findByRole("button",{name:"编辑兴趣"}));await screen.findByRole("button",{name:"保存兴趣"});fireEvent.keyDown(screen.getByRole("form",{name:"此关注的兴趣"}),{key:"Escape"});expect(screen.queryByRole("button",{name:"保存兴趣"})).toBeNull();expect(fetcher.mock.calls.every(([,i])=>!i.method||i.method==="GET")).toBe(true);
});
it("guards double submit while preserving the single persisted command",async()=>{
 let resolve!:(v:ReturnType<typeof response>)=>void;const fetcher=vi.fn((_u:string,i:RequestInit)=>i.method==="PUT"?new Promise(r=>{resolve=r;}):Promise.resolve(response(detail())));vi.stubGlobal("fetch",fetcher);render(view());await edit();
 const form=save().closest("form")!;fireEvent.submit(form);fireEvent.submit(form);expect(fetcher.mock.calls.filter(([,i])=>i.method==="PUT")).toHaveLength(1);await act(async()=>resolve(response({applied_source_policy_revision_id:"r1",current_source_policy_revision_id:"r1",historical_replay:false})));await screen.findByText("Interests saved.");
});
