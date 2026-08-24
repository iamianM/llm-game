import { redirect } from "next/navigation";
import { DEFAULT_SCENARIO } from "../../../lib/eval-showcase";

export default function ScenariosIndexPage() {
  redirect(`/evals/scenarios/${DEFAULT_SCENARIO}`);
}
