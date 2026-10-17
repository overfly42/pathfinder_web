import { formatBreakdown } from './breakdown';
import { gearLine } from './gearSummary';
import { formatSpellComponents, type Language } from './spellComponents';
import { alignmentLabel } from './alignment';
import type { Character } from '../types/character';

/** The built-in PDF fonts only cover WinAnsi — swap the few common glyphs outside it. */
function clean(text: string | null | undefined): string {
  return (text ?? '')
    .replace(/[‐-‒−]/g, '-')
    .replace(/[‘’]/g, "'")
    .replace(/[“”„]/g, '"')
    .replace(/≥/g, '>=')
    .replace(/≤/g, '<=')
    .split('')
    .map((ch) => (ch === '\n' || /[ -ÿ–—•…€]/.test(ch) ? ch : '?'))
    .join('');
}

const oneLine = (text: string | undefined) => (text ? text.replace(/\n/g, ', ') : '');

/** Builds the full character sheet as a text-based A4 PDF (selectable text, real tables) and
 *  triggers the download. jsPDF is loaded lazily so it stays out of the main bundle. */
export async function exportCharacterPdf(character: Character, language: Language) {
  const [{ jsPDF }, { default: autoTable }] = await Promise.all([import('jspdf'), import('jspdf-autotable')]);
  const doc = new jsPDF({ unit: 'mm', format: 'a4' });
  const margin = 10;
  const pageWidth = doc.internal.pageSize.getWidth();
  let y = margin;

  type Cell = string | { content: string; colSpan?: number; styles?: Record<string, unknown> };
  const table = (head: string[], body: Cell[][], opts: { colWidths?: Record<number, number>; fontSize?: number } = {}) => {
    autoTable(doc, {
      startY: y,
      head: [head.map(clean)],
      body: body.map((row) => row.map((c) => (typeof c === 'string' ? clean(c) : { ...c, content: clean(c.content) }))) as never,
      margin: { left: margin, right: margin },
      theme: 'grid',
      styles: { fontSize: opts.fontSize ?? 8, cellPadding: 1.2, lineColor: [150, 150, 150], lineWidth: 0.1, textColor: 20 },
      headStyles: { fillColor: [235, 235, 235], textColor: 20, fontStyle: 'bold' },
      columnStyles: Object.fromEntries(Object.entries(opts.colWidths ?? {}).map(([k, w]) => [k, { cellWidth: w }])),
    });
    y = (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 3;
  };

  const ensureSpace = (needed: number) => {
    if (y + needed > doc.internal.pageSize.getHeight() - margin) {
      doc.addPage();
      y = margin;
    }
  };
  const heading = (text: string) => {
    ensureSpace(20);
    doc.setFont('helvetica', 'bold').setFontSize(11);
    doc.text(clean(text).toUpperCase(), margin, y + 4);
    doc.setLineWidth(0.4).line(margin, y + 5.5, pageWidth - margin, y + 5.5);
    y += 8;
  };
  const subheading = (text: string) => {
    ensureSpace(16);
    doc.setFont('helvetica', 'bold').setFontSize(9);
    doc.text(clean(text), margin, y + 3);
    y += 4.5;
  };
  const paragraph = (text: string, size = 8.5) => {
    doc.setFont('helvetica', 'normal').setFontSize(size);
    const lines = doc.splitTextToSize(clean(text), pageWidth - 2 * margin) as string[];
    ensureSpace(lines.length * (size * 0.45) + 2);
    doc.text(lines, margin, y + 3);
    y += lines.length * (size * 0.45) + 2;
  };

  // Header
  doc.setFont('helvetica', 'bold').setFontSize(20);
  doc.text(clean(character.name), margin, y + 7);
  y += 10;
  paragraph(
    `${character.race} - ${character.className}${character.archetype ? ` (${character.archetype})` : ''} - Stufe ${character.level}` +
      (character.alignment ? ` - ${alignmentLabel(character.alignment)}` : ''),
    10,
  );

  const hp = character.hp;
  const movement = [
    `Land ${character.speed}`,
    character.climbSpeed && `Klettern ${character.climbSpeed}`,
    character.swimSpeed && `Schwimmen ${character.swimSpeed}`,
    character.flySpeed && `Fliegen ${character.flySpeed}${character.flyManeuverability ? ` (${character.flyManeuverability})` : ''}`,
  ].filter(Boolean) as string[];
  table(
    ['TP', 'RK', 'Auf dem falschen Fuss', 'Initiative', 'Bewegung'],
    [[
      `${hp.current}/${hp.max}${hp.temporary > 0 ? ` (+${hp.temporary} temp.)` : ''}`,
      String(character.armorClass),
      String(character.armorClassFlatFooted),
      character.initiative,
      movement.join(', '),
    ]],
    { fontSize: 9 },
  );
  if (character.armorClassBreakdown?.length) paragraph(`RK: ${oneLine(formatBreakdown(character.armorClassBreakdown))}`, 7.5);
  if (character.armorClassFlatFootedBreakdown?.length) {
    paragraph(`Auf dem falschen Fuss: ${oneLine(formatBreakdown(character.armorClassFlatFootedBreakdown))}`, 7.5);
  }

  heading('Attribute');
  table(
    ['Attribut', 'Wert', 'Mod.', 'Schaden', 'Zusammensetzung'],
    character.abilities.map((a) => [a.label, String(a.score), a.mod, a.damage > 0 ? `-${a.damage}` : '', oneLine(formatBreakdown(a.breakdown))]),
    { colWidths: { 1: 16, 2: 16, 3: 18 } },
  );

  heading('Rettungswuerfe & Kampfwerte');
  table(['Wert', 'Bonus'], [...character.saves, ...character.combat].map((e) => [e.label, e.value]), { colWidths: { 1: 40 } });

  if (character.weaponAttacks.length) {
    heading('Waffen');
    table(
      ['Waffe', 'Hand', 'Angriff', 'Schaden', 'Hinweis'],
      character.weaponAttacks.map((w) => [w.name, w.hand, w.attackBonus, w.damage, w.note ?? '']),
    );
  }

  heading('Fertigkeiten');
  table(
    ['Fertigkeit', 'Wert', 'Zusammensetzung / Hinweis'],
    character.skills.map((s) => [s.label, s.value, [oneLine(formatBreakdown(s.breakdown)), s.note].filter(Boolean).join(' - ')]),
    { colWidths: { 1: 16 } },
  );

  const described = (
    title: string,
    entries: { name: string; description: string; isSecondary?: boolean; summary?: string | null }[],
  ) => {
    if (!entries.length) return;
    heading(title);
    table(
      ['Name', 'Beschreibung'],
      entries.map((e) => [
        e.name + (e.isSecondary ? ' (Sekundaerklasse)' : ''),
        e.summary ? `[${e.summary}] ${e.description}` : e.description,
      ]),
      { colWidths: { 0: 45 } },
    );
  };
  described('Talente', character.feats);
  described('Wesenszuege', character.traits);
  described('Klassenfaehigkeiten', character.classFeatures);
  if (character.favoredClassBonuses?.length) {
    subheading('Bevorzugte Klasse');
    table(
      ['Name', 'Gewaehlt', 'Bonus', 'Beschreibung'],
      character.favoredClassBonuses.map((b) => [b.name, `${b.pickCount}x`, b.currentBonus !== null ? `+${b.currentBonus}` : '-', b.description]),
      { colWidths: { 0: 40, 1: 18, 2: 14 } },
    );
  }
  described('Rasseneigenschaften', character.raceAbilities);

  // Spellbook entries (full text, independent of today's preparation) are the spell list; casters
  // without a spellbook (divine/spontaneous) fall back to their known spells.
  const bookGrades = character.spellbook.filter((g) => !g.locked && g.spells.length > 0);
  const usesSpellbook = bookGrades.length > 0;
  const spellGrades = usesSpellbook ? bookGrades : character.spellsKnown.filter((g) => !g.locked && g.spells.length > 0);
  if (spellGrades.length || character.activatableSpells.length) {
    heading(usesSpellbook ? 'Zauberbuch' : 'Zauber');
    if (character.activatableSpells.length) paragraph(`Jederzeit wirkbar: ${character.activatableSpells.map((s) => s.name).join(', ')}`);
    for (const grade of spellGrades) {
      subheading(
        `Grad ${grade.grade}${grade.dc != null ? ` - SG ${grade.dc}` : ''}${grade.perDay != null ? ` - ${grade.perDay} pro Tag` : ''}`,
      );
      table(
        ['Zauber', 'Schule', 'Zeit', 'Komp.', 'Reichw.', 'Ziel/Gebiet', 'Dauer', 'RW', 'ZR'],
        grade.spells.flatMap((s): Cell[][] => {
          const main: Cell[] = [
            { content: s.name, styles: { fontStyle: 'bold', fillColor: [246, 246, 246] } },
            s.school ?? '-',
            s.castingTime ?? '-',
            formatSpellComponents(s.components, language),
            s.range ?? '-',
            s.target ?? '-',
            s.duration ?? '-',
            s.savingThrow ?? '-',
            s.spellResistance ?? '-',
          ];
          return s.description ? [main, [{ content: s.description, colSpan: 9, styles: { fontSize: 6.5 } }]] : [main];
        }),
        { fontSize: 7, colWidths: { 0: 26, 1: 20, 2: 15, 3: 20, 4: 19, 5: 24, 6: 20, 7: 18, 8: 14 } },
      );
    }
  }

  heading('Ausruestung');
  if (character.equipmentSlots.length) {
    subheading('Ausruestungsplaetze');
    table(
      ['Platz', 'Angelegt'],
      character.equipmentSlots.map((slot) => [slot.label, slot.options.find((o) => o.value === slot.selected)?.label ?? (slot.selected || '-')]),
      { colWidths: { 0: 50 } },
    );
  }
  subheading('Inventar');
  table(['Anz.', 'Gegenstand', 'Details'], character.gear.map((i) => [String(i.qty), i.name, gearLine(i)]), { colWidths: { 0: 14, 1: 55 } });
  if (character.wands?.length) {
    subheading('Zauberstaebe');
    table(
      ['Zauber', 'Grad', 'ZS', 'Ladungen'],
      character.wands.map((w) => [w.spellName, String(w.spellGrade), String(w.casterLevel), `${w.chargesRemaining}/${w.maxCharges}`]),
    );
  }

  const pages = doc.getNumberOfPages();
  for (let p = 1; p <= pages; p++) {
    doc.setPage(p);
    doc.setFont('helvetica', 'normal').setFontSize(7).setTextColor(100);
    doc.text(`${clean(character.name)} - Seite ${p}/${pages}`, pageWidth / 2, doc.internal.pageSize.getHeight() - 4, { align: 'center' });
  }

  doc.save(`${character.name.replace(/[^\w\-äöüÄÖÜß]+/g, '_') || 'charakter'}.pdf`);
}
