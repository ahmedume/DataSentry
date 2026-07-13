// Single source of truth for scroll progress (0 -> 1).
// Shared between the DOM overlay (Framer Motion) and the R3F camera (useFrame),
// so the camera and the copy never desync. Updated imperatively to avoid re-renders.
export const scrollStore: { current: number; pointer: { x: number; y: number } } = {
  current: 0,
  pointer: { x: 0, y: 0 },
};
