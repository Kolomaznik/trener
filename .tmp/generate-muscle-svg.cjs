const fs = require("fs");
const path = require("path");

const root = process.cwd();
const srcDir = path.join(root, ".tmp", "react-native-body-highlighter", "assets");
const outDir = path.join(root, "FRONTEND", "src", "assets");

function findMatchingBrace(text, startIndex) {
  let depth = 0;
  let inString = false;
  let quote = "";
  let escape = false;

  for (let i = startIndex; i < text.length; i++) {
    const ch = text[i];

    if (inString) {
      if (escape) {
        escape = false;
      } else if (ch === "\\") {
        escape = true;
      } else if (ch === quote) {
        inString = false;
        quote = "";
      }
      continue;
    }

    if (ch === '"' || ch === "'") {
      inString = true;
      quote = ch;
      continue;
    }

    if (ch === "{") depth += 1;
    if (ch === "}") {
      depth -= 1;
      if (depth === 0) return i;
    }
  }

  return -1;
}

function parseBodyFile(tsSource) {
  const parts = [];
  const slugRe = /slug:\s*"([^"]+)"/g;
  let slugMatch;

  while ((slugMatch = slugRe.exec(tsSource)) !== null) {
    const slug = slugMatch[1];
    const slugIdx = slugMatch.index;
    const partStart = tsSource.lastIndexOf("{", slugIdx);
    if (partStart < 0) continue;

    const partEnd = findMatchingBrace(tsSource, partStart);
    if (partEnd < 0) continue;

    const block = tsSource.slice(partStart, partEnd + 1);

    const pathStart = block.indexOf("path:");
    if (pathStart < 0) continue;
    const pathObjStart = block.indexOf("{", pathStart);
    if (pathObjStart < 0) continue;
    const absolutePathObjStart = partStart + pathObjStart;
    const absolutePathObjEnd = findMatchingBrace(tsSource, absolutePathObjStart);
    if (absolutePathObjEnd < 0) continue;
    const pathBlock = tsSource.slice(absolutePathObjStart, absolutePathObjEnd + 1);

    const sidePaths = { common: [], left: [], right: [] };
    const sideRe = /(common|left|right):\s*\[([\s\S]*?)\]/g;
    let sideMatch;
    while ((sideMatch = sideRe.exec(pathBlock)) !== null) {
      const side = sideMatch[1];
      const arrBlock = sideMatch[2];
      const strRe = /"((?:\\.|[^"\\])*)"/g;
      let strMatch;
      while ((strMatch = strRe.exec(arrBlock)) !== null) {
        sidePaths[side].push(strMatch[1].replace(/\\"/g, '"'));
      }
    }

    parts.push({ slug, sidePaths });
  }

  return parts;
}

function bodyPartsToSvg(parts, cfg) {
  const groups = [];
  for (const part of parts) {
    const all = [...part.sidePaths.common, ...part.sidePaths.left, ...part.sidePaths.right];
    if (all.length === 0) continue;
    const paths = all.map((d) => `    <path d="${d}" />`).join("\n");
    groups.push(`  <g id="${part.slug}" data-slug="${part.slug}">\n${paths}\n  </g>`);
  }

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${cfg.viewBox}" role="img" aria-labelledby="${cfg.idPrefix}-title ${cfg.idPrefix}-desc">\n  <title id="${cfg.idPrefix}-title">${cfg.title}</title>\n  <desc id="${cfg.idPrefix}-desc">${cfg.desc}</desc>\n  <g id="body-parts" fill="#3f3f3f" fill-opacity="0.9" stroke="none">\n${groups.join("\n")}\n  </g>\n</svg>\n`;
}

const frontTs = fs.readFileSync(path.join(srcDir, "bodyFront.ts"), "utf8");
const backTs = fs.readFileSync(path.join(srcDir, "bodyBack.ts"), "utf8");

const frontParts = parseBodyFile(frontTs);
const backParts = parseBodyFile(backTs);

const frontSvg = bodyPartsToSvg(frontParts, {
  viewBox: "0 0 724 1448",
  idPrefix: "male-front",
  title: "Male body muscle map front",
  desc: "Body-part paths adapted for web SVG from MIT-licensed react-native-body-highlighter.",
});

const backSvg = bodyPartsToSvg(backParts, {
  viewBox: "724 0 724 1448",
  idPrefix: "male-back",
  title: "Male body muscle map back",
  desc: "Body-part paths adapted for web SVG from MIT-licensed react-native-body-highlighter.",
});

fs.writeFileSync(path.join(outDir, "muscle-map-front.svg"), frontSvg, "utf8");
fs.writeFileSync(path.join(outDir, "muscle-map-back.svg"), backSvg, "utf8");

const notice = `This project includes adapted SVG path data from:\n\nreact-native-body-highlighter\nhttps://github.com/HichamELBSI/react-native-body-highlighter\n\nLicense: MIT\nCopyright (c) 2022 ELABBASSI Hicham\n\nThe original copyright and license terms apply to the adapted portions.\n`;

fs.writeFileSync(path.join(root, "FRONTEND", "THIRD_PARTY_NOTICES.md"), notice, "utf8");

console.log(`front parts: ${frontParts.length}`);
console.log(`back parts: ${backParts.length}`);
console.log("generated SVG and notices");
