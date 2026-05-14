import { GameStage } from "../../../components/stage/GameStage";

export default function PlayPage({ params }: { params: { sessionId: string } }) {
  return <GameStage sessionId={params.sessionId} />;
}
