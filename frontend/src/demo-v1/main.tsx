import React from "react";
import ReactDOM from "react-dom/client";
import { DemoApp } from "./App";
import "./styles.css";

const initialExperience = new URLSearchParams(window.location.search).get("start") === "workspace" ? "workspace" : "onboarding";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode><DemoApp initialExperience={initialExperience} /></React.StrictMode>,
);
