import { ConsoleWorkspace } from "@/components/ConsoleWorkspace";
import { preview } from "@/lib/preview";

export default function Page() {
  return <ConsoleWorkspace preview={preview} />;
}
