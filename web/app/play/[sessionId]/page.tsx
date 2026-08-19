import { GameStage } from "../../../components/stage/GameStage";

export default async function PlayPage({
  params
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  return <GameStage sessionId={sessionId} />;
}
