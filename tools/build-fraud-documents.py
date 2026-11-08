"""Rebuild exact, legible fictional document excerpts (no image generation for text)."""
from pathlib import Path
from html import escape

OUT = Path(__file__).resolve().parents[1]/'mia/mia-fraude/assets'


def document(name, issuer, title, reference, rows, total=None, note=''):
    # 900 × 640: one phone-sized excerpt, not an unreadable full A4 invoice.
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="640" viewBox="0 0 900 640">',
         '<rect width="900" height="640" fill="#faf9f4"/>',
         '<path d="M0 0h900v12H0z" fill="#263c42"/>',
         '<g font-family="Arial,sans-serif" fill="#25383c">',
         f'<text x="44" y="65" font-size="23" font-weight="700">{escape(issuer)}</text>',
         f'<text x="44" y="122" font-size="40" font-weight="700">{escape(title)}</text>',
         f'<text x="44" y="163" font-size="23" fill="#657479">{escape(reference)}</text>',
         '<path d="M44 186H856" stroke="#cbd2ce" stroke-width="2"/>']
    for i, (label, value) in enumerate(rows):
        y=221+i*79
        s += [f'<text x="44" y="{y}" font-size="21" fill="#637475">{escape(label)}</text>',
              f'<text x="44" y="{y+37}" font-size="32" font-weight="700">{escape(value)}</text>']
    if total:
        s += ['<rect x="520" y="465" width="336" height="104" rx="2" fill="#e8ede7"/>',
              f'<text x="540" y="500" font-size="22">{escape(total[0])}</text>',
              f'<text x="540" y="548" font-size="40" font-weight="700">{escape(total[1])}</text>']
    if note:s.append(f'<text x="44" y="568" font-size="24">{escape(note)}</text>')
    s += ['<path d="M44 593H856" stroke="#cbd2ce"/>',
          '<text x="44" y="621" font-size="17" fill="#87928c">Extrait pour le jeu · document et identités fictifs</text></g></svg>']
    (OUT/name).write_text('\n'.join(s))


document('case-02-b.svg','EXPERTISE AUTOMOBILE / Dossier A-208','Compte rendu de contrôle','Visite du 02.11.2026 · pièce jointe 2/2',[
 ('Véhicule examiné','Coupé noir · numéro de série contrôlé'),
 ('Constat sur place','Aile, phare et portière côté gauche'),
 ('Comparaison avec la déclaration','Dommages et véhicule concordants'),
 ('Éléments examinés','Photographie + constat + inspection')])
document('case-03-a.svg','GESTION SINISTRES / Déclaration D-413','Déclaration automobile','Accident du 28.10.2026 · assuré : Camille Leroy',[
 ('Véhicule assuré','Compacte grise · immatriculation'),
 ('Numéro d’immatriculation','AB-274-CD'),
 ('Dommages déclarés','Pare-chocs avant et peinture'),
 ('Réparateur choisi','Atelier des Peupliers')])
document('case-03-b.svg','ATELIER DES PEUPLIERS','Facture de réparation','F-2026-0413 · 03.11.2026 · client : Camille Leroy',[
 ('Véhicule facturé','Compacte grise · immatriculation'),
 ('Numéro d’immatriculation','AB-247-CD'),
 ('Intervention','Pare-chocs avant / mise en peinture')],('Total TTC','1 872,00 €'))
document('case-04-a.svg','CARROSSERIE DU CANAL','Facture de réparation','FC-1086 · 04.11.2026 · client : Sam Robin',[
 ('Réparation et peinture','Total TTC : 1 440,00 €'),
 ('Acompte reçu le 27.10.2026','400,00 € · carte bancaire'),
 ('Solde à régler','1 040,00 €')],note='Facture : 1 440 € = acompte 400 € + solde 1 040 €')
document('case-04-b.svg','ESPACE BANCAIRE / Opération exécutée','Avis de virement','Extrait du 05.11.2026 · statut : exécuté',[
 ('Émetteur → bénéficiaire','Sam Robin → Carrosserie du Canal'),
 ('Motif du paiement','Solde facture FC-1086'),
 ('Date de valeur','05.11.2026')],('Montant transféré','1 040,00 €'))
document('case-06-a.svg','GESTION SINISTRES / Dossiers distincts','Coordonnées de règlement','Deux assurés · deux sinistres habitation',[
 ('Dossier H-201 · Alex Martin','Dégât des eaux · 18.10.2026'),
 ('Compte de remboursement','LU•• •••• •••• •••• 7849'),
 ('Dossier H-366 · Charlie Martin','Bris de vitre · 31.10.2026'),
 ('Compte de remboursement','LU•• •••• •••• •••• 7849')])
document('case-06-b.svg','RELEVÉ D’IDENTITÉ BANCAIRE','Attestation de compte','Émise le 02.11.2026 · extrait',[
 ('Titulaire 1','Alex Martin'),
 ('Titulaire 2','Charlie Martin'),
 ('Nature du compte','Compte joint · deux cotitulaires'),
 ('IBAN (masqué pour le jeu)','LU•• •••• •••• •••• 7849')])
