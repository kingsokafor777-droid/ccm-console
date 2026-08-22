import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ConsoleWorkspace } from "@/components/ConsoleWorkspace";
import { preview } from "@/lib/preview";

afterEach(cleanup);

describe("ConsoleWorkspace", () => {
  it("shows explicit synthetic and coverage boundaries", () => {
    render(<ConsoleWorkspace preview={preview} />);
    expect(screen.getByText("SYNTHETIC LOCAL PREVIEW")).toBeTruthy();
    expect(screen.getByText(/Missing or unavailable sources remain explicit coverage states/)).toBeTruthy();
    expect(screen.getByText("logging_coverage")).toBeTruthy();
  });

  it("switches between payload-blind evidence and coordination workbench views", () => {
    render(<ConsoleWorkspace preview={preview} />);
    fireEvent.click(screen.getByRole("button", { name: "Evidence explorer" }));
    expect(screen.getByText("Payload-blind evidence references")).toBeTruthy();
    expect(screen.getByText(/console shows no evidence payload/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Remediation workbench" }));
    expect(screen.getByText("Workstation boundary")).toBeTruthy();
    expect(screen.getByText(/Neither action executes remediation/i)).toBeTruthy();
  });
});
