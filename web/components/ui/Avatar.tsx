import Image from "next/image";
import type { IslanderLook } from "../../lib/look";
import { isRosterId, rosterSprite } from "../../lib/roster";
import { npcSprite } from "../../lib/scene/npc-art";
import { PlayerCrest } from "../look/PlayerCrest";

const PALETTE = ["#b9502f", "#5b7c4f", "#c8932a", "#4a8fb8", "#8a5f78", "#7c654f"];

type Size = "xs" | "sm" | "md" | "lg" | "xl" | "responsive";

export function Avatar({ id, name, size = "md", look = null }: { id: string; name: string; size?: Size; look?: IslanderLook | null }) {
  // A roster pick has a real face — crop its standee into the disc so the HUD,
  // couples list and finale all show the player's chosen islander. Legacy/
  // checkpoint sessions carry a look without a roster id and fall back to the
  // look-aware casting crest. NPCs keep their photo; unknown ids keep a
  // monogram disc.
  if (look && !isRosterId(look.characterId)) return <PlayerCrest look={look} name={name} size={size} />;
  const dimsMap: Record<Exclude<Size, "responsive">, number> = { xs: 22, sm: 30, md: 44, lg: 80, xl: 168 };
  const dims = size === "responsive" ? null : dimsMap[size];
  const color = PALETTE[Math.abs(hash(id)) % PALETTE.length];
  const image = look?.characterId && isRosterId(look.characterId) ? rosterSprite(look.characterId) : npcSprite(id);
  return (
    <div
      className="avatar-disc relative grid shrink-0 place-items-center overflow-hidden rounded-full font-display font-bold text-[var(--card)] shadow-[var(--shadow-md)]"
      style={dims ? {
        width: dims,
        height: dims,
        background: `radial-gradient(circle at 40% 30%, color-mix(in oklab, ${color} 84%, white), ${color}) , ${color}`,
        fontSize: Math.max(11, dims / 3.4),
        letterSpacing: "-0.02em",
        textShadow: "0 2px 8px rgba(0,0,0,.45)",
        fontStyle: "italic"
      } : {
        width: "var(--portrait-size, 168px)",
        height: "var(--portrait-size, 168px)",
        background: `radial-gradient(circle at 40% 30%, color-mix(in oklab, ${color} 84%, white), ${color}) , ${color}`,
        fontSize: "calc(var(--portrait-size, 168px) / 3.4)",
        letterSpacing: "-0.02em",
        textShadow: "0 2px 8px rgba(0,0,0,.45)",
        fontStyle: "italic"
      }}
      aria-label={name}
    >
      {image ? (
        <Image
          src={image}
          alt=""
          fill
          sizes={imageSizes(size)}
          className="object-cover"
          style={{ objectPosition: "50% 18%" }}
          aria-hidden
        />
      ) : initials(name)}
    </div>
  );
}

function imageSizes(size: Size) {
  if (size === "responsive") return "200px";
  if (size === "xl") return "168px";
  if (size === "lg") return "80px";
  if (size === "md") return "44px";
  if (size === "sm") return "30px";
  return "22px";
}

function initials(name: string) {
  if (name.toLowerCase() === "you") return "You";
  return name.trim().split(" ").filter(Boolean).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
}

function hash(value: string) {
  return [...value].reduce((acc, char) => acc + char.charCodeAt(0), 0);
}
