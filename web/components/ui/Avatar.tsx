import Image from "next/image";
import type { IslanderLook } from "../../lib/look";
import { PlayerCrest } from "../look/PlayerCrest";

const PALETTE = ["#b9502f", "#5b7c4f", "#c8932a", "#4a8fb8", "#8a5f78", "#7c654f"];

type Size = "xs" | "sm" | "md" | "lg" | "xl" | "responsive";

const IMAGE_BY_ID: Record<string, string> = {
  chloe: "/images/characters/chloe.webp",
  maya: "/images/characters/maya.webp",
  liam: "/images/characters/liam.webp",
  sophie_start: "/images/characters/sophie_start.webp",
  nia_start: "/images/characters/nia_start.webp",
  marcus_start: "/images/characters/marcus_start.webp",
  blake_start: "/images/characters/blake_start.webp",
  jordan_start: "/images/characters/jordan_start.webp",
  blake: "/images/characters/blake_start.webp",
  jordan: "/images/characters/jordan_start.webp",
  marcus: "/images/characters/marcus_start.webp",
  sophie: "/images/characters/sophie_start.webp",
  nia: "/images/characters/nia_start.webp",
  // Casa Amor bombshells (engine ids from src/game/engine/casa_amor.py) — without
  // these they showed a monogram disc instead of a photo in the cast list,
  // couples panel and finale. Borrow gender-matched heart-throb headshots until
  // each gets bespoke art.
  beau: "/images/characters/sam_ht.webp",
  jules: "/images/characters/sam_ht.webp",
  mateo: "/images/characters/ellis_ht.webp",
  noor: "/images/characters/talia_ht.webp",
  sasha: "/images/characters/talia_ht.webp",
  zara: "/images/characters/riley_ht.webp",
  sam_ht: "/images/characters/sam_ht.webp",
  riley_ht: "/images/characters/riley_ht.webp",
  ellis_ht: "/images/characters/ellis_ht.webp",
  talia_ht: "/images/characters/talia_ht.webp"
};

export function Avatar({ id, name, size = "md", look = null }: { id: string; name: string; size?: Size; look?: IslanderLook | null }) {
  // The player has no photoreal headshot — when their chosen look is supplied,
  // render the look-aware casting crest (skin/hair/vibe) so the avatar that
  // travels through the HUD, profile, couples list and finale is unmistakably
  // theirs. NPCs keep their photo; unknown ids keep the monogram disc.
  if (look) return <PlayerCrest look={look} name={name} size={size} />;
  const dimsMap: Record<Exclude<Size, "responsive">, number> = { xs: 22, sm: 30, md: 44, lg: 80, xl: 168 };
  const dims = size === "responsive" ? null : dimsMap[size];
  const color = PALETTE[Math.abs(hash(id)) % PALETTE.length];
  const image = IMAGE_BY_ID[id];
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
