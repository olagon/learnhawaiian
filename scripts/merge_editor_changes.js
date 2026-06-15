// Usage: node scripts/merge_editor_changes.js <changes.json> [data.js]
// Applies editor export (edit/delete/add) onto data.js, preserving formatting.
const fs = require("fs");
const changesPath = process.argv[2];
const dataPath = process.argv[3] || "data.js";
if(!changesPath){ console.error("Provide a changes.json path."); process.exit(1); }

const changes = JSON.parse(fs.readFileSync(changesPath,"utf8"));
let src = fs.readFileSync(dataPath,"utf8");
let V = JSON.parse(src.slice(src.indexOf("["), src.lastIndexOf("]")+1));
const byId = {}; V.forEach(w=>byId[w.ID]=w);
let maxId = Math.max(...V.map(w=>w.ID));

let nEdit=0,nDel=0,nAdd=0,warn=[];
const delIds = new Set();
(changes.changes||[]).forEach(c=>{
  if(c.action==="edit"){
    const w=byId[c.id];
    if(!w){ warn.push("edit: id "+c.id+" not found"); return; }
    w.Hawaiian=c.updated.Hawaiian; w.English=c.updated.English; w.Type=c.updated.Type; w.Tier=Number(c.updated.Tier);
    nEdit++;
  } else if(c.action==="delete"){
    if(!byId[c.id]){ warn.push("delete: id "+c.id+" not found"); return; }
    delIds.add(c.id); nDel++;
  } else if(c.action==="add"){
    V.push({ID:++maxId, Hawaiian:c.entry.Hawaiian, English:c.entry.English, Type:c.entry.Type, Tier:Number(c.entry.Tier)});
    nAdd++;
  }
});
V = V.filter(w=>!delIds.has(w.ID));

function ser(w){return [" {",
 '   "ID": '+w.ID+",",
 '   "Hawaiian": '+JSON.stringify(w.Hawaiian)+",",
 '   "English": '+JSON.stringify(w.English)+",",
 '   "Type": '+JSON.stringify(w.Type)+",",
 '   "Tier": '+w.Tier," }"].join("\n");}
fs.writeFileSync(dataPath,"const vocabularyData = [\n"+V.map(ser).join(",\n")+"\n];\n");
console.log(`Applied: ${nEdit} edits, ${nDel} deletions, ${nAdd} additions. Total now ${V.length}.`);
if(warn.length) console.log("Warnings:\n  "+warn.join("\n  "));
