/* Coordinates refer to the actual image, never the letterboxed container. */
export function imageRect(box, naturalWidth, naturalHeight) {
  const scale = Math.min(box.width / naturalWidth, box.height / naturalHeight);
  const width = naturalWidth * scale, height = naturalHeight * scale;
  return {left:box.left+(box.width-width)/2, top:box.top+(box.height-height)/2, width, height};
}
export function imagePoint(clientX, clientY, rect) {
  const x=(clientX-rect.left)/rect.width,y=(clientY-rect.top)/rect.height;
  return x>=0 && x<=1 && y>=0 && y<=1 ? {x,y} : null;
}
export function swipeDecision(dx, dy, width) {
  if (Math.abs(dx) < Math.min(85,width*.24) || Math.abs(dx)<Math.abs(dy)*1.4) return null;
  return dx>0;
}
