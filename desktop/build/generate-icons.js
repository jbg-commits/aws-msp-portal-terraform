const sharp = require("sharp");
const pngToIco = require("png-to-ico");
const fs = require("fs");
const path = require("path");

const SIZES = [16, 32, 48, 256];
const svgPath = path.join(__dirname, "logo.svg");

async function main() {
  const svgBuffer = fs.readFileSync(svgPath);
  const pngs = {};
  for (const size of SIZES) {
    pngs[size] = await sharp(svgBuffer, { density: 384 }).resize(size, size).png().toBuffer();
  }

  fs.writeFileSync(
    path.join(__dirname, "icon.ico"),
    await pngToIco([pngs[16], pngs[32], pngs[48], pngs[256]])
  );
  fs.writeFileSync(
    path.join(__dirname, "tray.ico"),
    await pngToIco([pngs[16], pngs[32]])
  );

  console.log("Generated build/icon.ico and build/tray.ico");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
