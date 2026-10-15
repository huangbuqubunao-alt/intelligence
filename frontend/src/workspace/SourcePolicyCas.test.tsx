import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ExistingSourceForm } from "./App";
import { UiLanguageProvider } from "./uiLanguage";
const source={source_id:"source-1",canonical_url:"https://www.youtube.com/watch?v=abc",enabled:true,processing_policy:"STANDARD_INTELLIGENCE",display_name:"Video",last_error:null};
const policy={source_policy_revision_id:"r0",initial_history_count:3,per_run_max_new_videos:10,focus_rules:["robotics"],ignore_rules:[],distillation_style:"BALANCED"};
const modes={focus:"OVERRIDE",ignore:"OVERRIDE",style:"OVERRIDE"} as const;
const response=(value:unknown,ok=true)=>({ok,status:ok?200:409,json:async()=>value});
const renderForm=()=>render(<UiLanguageProvider><ExistingSourceForm source={source} policy={policy} policyModes={modes} schedules={[{schedule_id:"existing",frequency:"DAILY",local_time:"13:25",enabled:true}]} onSaved={vi.fn()} onClose={vi.fn()} /></UiLanguageProvider>);
const save=()=>screen.getByRole("button",{name:"Save changes"});
beforeEach(()=>localStorage.setItem("yia.ui-language","en"));afterEach(()=>vi.unstubAllGlobals());
it("checks policy CAS before any Source or automation writes and preserves conflicting draft",async()=>{
 const fetcher=vi.fn(async(_u:string,i:RequestInit)=>i.method==="PUT"?response({error:{code:"CONFLICT",message:"conflict"}},false):response({policy}));vi.stubGlobal("fetch",fetcher);renderForm();
 fireEvent.change(screen.getByLabelText("Focus"),{target:{value:"my draft"}});fireEvent.click(save());
 await screen.findByText("Interests changed elsewhere. Your draft is preserved. Reload the current version before saving again.");
 expect(fetcher.mock.calls.filter(([,i])=>i.method&&i.method!=="GET").map(([,i])=>i.method)).toEqual(["PUT"]);
 expect(JSON.parse(fetcher.mock.calls.find(([,i])=>i.method==="PUT")![1].body as string).expected_source_policy_revision_id).toBe("r0");
 expect((screen.getByLabelText("Focus") as HTMLInputElement).value).toBe("my draft");expect((save() as HTMLButtonElement).disabled).toBe(true);
});
it.each([false, true])("resumes only unfinished steps after Source PATCH failure without replaying policy or changing the daily schedule (conflict=%s)",async conflict=>{
 let patches=0;const fetcher=vi.fn(async(_u:string,i:RequestInit)=>{if(i.method==="PUT")return response({applied_source_policy_revision_id:"r1",current_source_policy_revision_id:"r1",historical_replay:false});if(i.method==="PATCH"&&++patches===1){if(conflict)return response({error:{code:"CONFLICT",message:"source conflict"}},false);throw new TypeError("offline");}return response({policy});});vi.stubGlobal("fetch",fetcher);renderForm();fireEvent.click(save());
 await screen.findByText("Policy saved. Source settings could not be saved. Retry resumes remaining steps.");fireEvent.click(save());await waitFor(()=>expect(fetcher.mock.calls.filter(([,i])=>i.method==="POST")).toHaveLength(1));
 expect(fetcher.mock.calls.filter(([,i])=>i.method&&i.method!=="GET").map(([,i])=>i.method)).toEqual(["PUT","PATCH","PATCH","POST"]);
 const body=JSON.parse(fetcher.mock.calls.find(([,i])=>i.method==="POST")![1].body as string);expect(body.frequency).toBe("DAILY");expect(body.local_time).toBe("13:25");expect(body.schedule_id).toBe("existing");
});
it("retries an uncertain policy response using the same complete command",async()=>{
 let puts=0;const fetcher=vi.fn(async(_u:string,i:RequestInit)=>{if(i.method==="PUT"){if(++puts===1)throw new TypeError("offline");return response({applied_source_policy_revision_id:"r1",current_source_policy_revision_id:"r1",historical_replay:false});}return response({policy});});vi.stubGlobal("fetch",fetcher);renderForm();fireEvent.click(save());await screen.findByRole("alert");fireEvent.click(save());await waitFor(()=>expect(puts).toBe(2));
 const bodies=fetcher.mock.calls.filter(([,i])=>i.method==="PUT").map(([,i])=>i.body);expect(bodies[1]).toBe(bodies[0]);
});
it("blocks missing revisions and unknown persisted enums until a valid explicit read, preserving draft",async()=>{
 const fetcher=vi.fn(async(_u:string,_i:RequestInit)=>response({source,policy:{...policy,source_policy_revision_id:"r1"},policy_modes:modes}));vi.stubGlobal("fetch",fetcher);
 render(<UiLanguageProvider><ExistingSourceForm source={source} policy={{...policy,distillation_style:"UNKNOWN"}} policyModes={modes} onSaved={vi.fn()} onClose={vi.fn()} /></UiLanguageProvider>);
 expect((save() as HTMLButtonElement).disabled).toBe(true);fireEvent.change(screen.getByLabelText("Focus"),{target:{value:"retained draft"}});
 fireEvent.click(screen.getByRole("button",{name:"Reload current interests"}));await waitFor(()=>expect((save() as HTMLButtonElement).disabled).toBe(false));expect((screen.getByLabelText("Focus") as HTMLInputElement).value).toBe("retained draft");
});
