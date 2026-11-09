"""Build fictional evidence with distinct document layouts and exact arithmetic.

Coordinates are explicit so app/fraud_cases.json can annotate the actual field.
No customer document or externally loaded font is used.
"""
from pathlib import Path
from html import escape
import base64

OUT = Path(__file__).resolve().parents[1] / 'mia/mia-fraude/assets'


class Sheet:
    def __init__(self, name, width, height, color='#fffefb', ink='#283038'):
        self.name, self.width, self.height = name, width, height
        self.ink = ink
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
                      f'<rect width="{width}" height="{height}" fill="{color}"/>',
                      '<g font-family="Arial,sans-serif">']

    def rect(self, x, y, w, h, color, stroke=None):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}"'+
                          (f' stroke="{stroke}" stroke-width="2"' if stroke else '')+'/>')

    def text(self, x, y, value, size=24, weight=400, color=None, anchor='start'):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color or self.ink}" text-anchor="{anchor}">{escape(value)}</text>')

    def line(self, x, y, x2, y2, color='#d7dadd'):
        self.parts.append(f'<path d="M{x} {y}L{x2} {y2}" stroke="{color}" stroke-width="2"/>')

    def field(self, x, y, label, value, width=330):
        self.text(x, y, label, 19, color='#75818a')
        self.text(x, y+34, value, 29, 600)
        self.line(x, y+48, x+width, y+48)

    def save(self):
        self.text(36, self.height-20, 'Document fictif · jeu de démonstration', 14, color='#8d9598')
        (OUT/self.name).write_text('\n'.join(self.parts+['</g></svg>']))


def report():
    s=Sheet('case-02-b.svg',900,700,'#f2f1eb')
    s.rect(0,0,18,700,'#566561')
    s.text(46,60,'BUREAU DE CONTRÔLE AUTOMOBILE',23,700)
    s.text(46,119,'RAPPORT DE VISITE',38,700)
    s.text(46,158,'Référence A-208 / visite du 02 novembre 2026',23)
    s.line(46,185,854,185)
    s.field(46,228,'VÉHICULE EXAMINÉ','Coupé noir',360)
    s.field(470,228,'IDENTIFICATION','N° de série contrôlé',360)
    s.text(46,336,'Observations de l’expert',26,700)
    for i,t in enumerate(['Choc latéral gauche : aile, phare et portière.','Les déformations suivent le même axe d’impact.','Photographies et constat examinés lors de la visite.']):
        s.text(46,380+i*39,t,25)
    s.line(46,490,854,490)
    s.text(46,533,'Rapprochement avec les pièces du dossier',21,color='#66766b')
    s.text(46,574,'Dommages et véhicule concordants.',30,600)
    s.text(46,632,'Visite réalisée sur place / compte rendu clos',20,color='#66766b')
    s.save()


def declaration():
    s=Sheet('case-03-a.svg',900,760,'#f8fafc')
    s.rect(0,0,900,82,'#25495b')
    s.text(38,53,'DÉCLARATION DE SINISTRE AUTOMOBILE',28,700,'#ffffff')
    s.text(38,124,'Dossier D-413',31,700)
    s.text(860,124,'Reçu le 29/10/2026',21,anchor='end')
    s.rect(38,155,824,45,'#e4ebef');s.text(52,186,'01  /  ASSURÉ ET VÉHICULE',22,700)
    s.field(52,241,'NOM ET PRÉNOM','Camille Leroy',360)
    s.field(475,241,'DATE DU SINISTRE','28/10/2026',370)
    s.field(52,345,'VÉHICULE','Compacte grise',360)
    s.field(475,345,'IMMATRICULATION','AB-274-CD',370)
    s.rect(38,423,824,45,'#e4ebef');s.text(52,454,'02  /  CIRCONSTANCES ET RÉPARATION',22,700)
    s.text(52,514,'Choc à l’avant du véhicule lors d’une manœuvre.',25)
    s.text(52,555,'Pare-chocs rayé et peinture endommagée.',25)
    s.field(52,617,'RÉPARATEUR DÉSIGNÉ','Atelier des Peupliers',770)
    s.text(52,710,'Déclaration transmise en ligne / pièces jointes : 2',19,color='#75818a')
    s.save()


def garage_invoice():
    s=Sheet('case-03-b.svg',820,1000,'#fffdf7')
    s.text(48,68,'AP',52,700,'#9a5140')
    s.text(150,54,'ATELIER DES PEUPLIERS',25,700)
    s.text(150,88,'Carrosserie · peinture · réparation',19,color='#8d7565')
    s.line(48,126,772,126,'#9a5140')
    s.text(48,183,'FACTURE',42,700)
    s.text(770,174,'F-2026-0413',25,700,anchor='end')
    s.text(770,210,'03 novembre 2026',21,anchor='end')
    s.text(48,265,'FACTURÉ À',18,color='#8d7565');s.text(48,305,'Camille Leroy',30,700)
    s.rect(48,347,724,106,'#f2ece0')
    s.text(66,379,'Véhicule : compacte grise',24)
    s.text(66,421,'Immatriculation : AB-247-CD',29,600)
    s.text(48,508,'DÉSIGNATION',19,700);s.text(768,508,'MONTANT HT',19,700,anchor='end')
    for i,(t,v) in enumerate([('Remplacement du pare-chocs','840,00 €'),('Préparation et peinture','510,00 €'),('Main-d’œuvre et ajustage','210,00 €')]):
        y=563+i*67;s.text(48,y,t,24);s.text(768,y,v,25,anchor='end');s.line(48,y+22,772,y+22)
    for y,k,v in [(794,'TOTAL HT','1 560,00 €'),(837,'TVA 20 %','312,00 €')]:
        s.text(420,y,k,22);s.text(768,y,v,24,anchor='end')
    s.rect(401,864,371,66,'#9a5140');s.text(418,908,'TTC',25,700,'#fff');s.text(754,908,'1 872,00 €',34,700,'#fff',anchor='end')
    s.text(48,961,'Paiement à réception · référence F-2026-0413',18,color='#8d7565')
    s.save()


def detailed_invoice():
    s=Sheet('case-04-a.svg',900,1180,'#fff')
    s.rect(45,42,65,65,'#264a41');s.text(77,87,'C',38,700,'#fff',anchor='middle')
    s.text(132,66,'CARROSSERIE DU CANAL',29,700,'#264a41')
    s.text(132,98,'Réparation automobile · devis et travaux',19,color='#65776b')
    s.text(45,160,'FACTURE FC-1086',37,700)
    s.text(855,156,'04/11/2026',25,anchor='end')
    s.field(45,211,'CLIENT','Sam Robin',350)
    s.field(485,211,'VÉHICULE','Berline · EF-630-GH',370)
    s.text(45,305,'Travaux effectués du 28 au 31 octobre 2026',22)
    s.text(45,342,'Remise en état du pare-chocs arrière',25,600)
    s.rect(45,380,810,45,'#e7ede9')
    for x,t,a in [(61,'DÉSIGNATION','start'),(591,'QTÉ','end'),(714,'P.U. HT','end'),(839,'TOTAL HT','end')]:s.text(x,410,t,19,700,anchor=a)
    rows=[('Dépose et repose du pare-chocs','2 h','75,00','150,00'),('Préparation / redressage','3 h','85,00','255,00'),('Élément de pare-chocs','1','430,00','430,00'),('Mise en peinture','3 h','85,00','255,00'),('Fournitures et consommables','1','110,00','110,00')]
    for i,row in enumerate(rows):
        y=470+i*66
        for x,t,a in [(61,row[0],'start'),(591,row[1],'end'),(714,row[2],'end'),(839,row[3],'end')]:s.text(x,y,t,22,anchor=a)
        s.line(45,y+24,855,y+24,'#e0e5e1')
    for y,k,v in [(830,'Total HT','1 200,00 €'),(872,'TVA 20 %','240,00 €'),(919,'Total TTC','1 440,00 €')]:
        s.text(535,y,k,24,600 if y==919 else 400);s.text(839,y,v,29 if y==919 else 25,600 if y==919 else 400,anchor='end')
    # A normal ledger in the footer, without spelling out the solution.
    s.text(45,991,'Règlements enregistrés',22,600)
    s.line(45,1010,855,1010)
    s.text(45,1049,'27/10/2026',21);s.text(235,1049,'CB · acompte commande',21);s.text(839,1049,'400,00 €',23,anchor='end')
    s.text(45,1110,'Garantie des réparations : 12 mois. Facture à conserver.',18,color='#7a837b')
    s.text(45,1139,'Référence à rappeler pour tout règlement : FC-1086.',18,color='#7a837b')
    s.save()


def transfer():
    s=Sheet('case-04-b.svg',680,890,'#f3f6f5')
    s.rect(0,0,680,125,'#253e3b');s.text(340,54,'ESPACE BANCAIRE',22,700,'#fff',anchor='middle')
    s.text(340,94,'Justificatif d’opération',27,600,'#fff',anchor='middle')
    s.text(340,198,'VIREMENT EXÉCUTÉ',22,700,'#386b54',anchor='middle')
    s.text(340,265,'1 040,00 €',55,700,anchor='middle')
    s.text(340,309,'05 novembre 2026',23,color='#7b8783',anchor='middle')
    for y,k,v in [(390,'DEPUIS','Sam Robin'),(494,'VERS','Carrosserie du Canal'),(598,'LIBELLÉ','FC-1086'),(702,'RÉFÉRENCE','VIR-051126-3807')]:s.field(46,y,k,v,588)
    s.text(46,835,'Émis depuis l’espace client / opération comptabilisée',17,color='#7b8783')
    s.save()


def accounts():
    s=Sheet('case-06-a.svg',960,660,'#f3f5f8')
    s.rect(0,0,960,83,'#323b49');s.text(35,51,'RÈGLEMENT DES SINISTRES',27,700,'#fff')
    for x,reference,name,claim,date in [(32,'H-201','Alex Martin','Dégât des eaux','18/10/2026'),(494,'H-366','Charlie Martin','Bris de vitre','31/10/2026')]:
        s.rect(x,122,434,459,'#fff','#d5dce3')
        s.text(x+22,171,'DOSSIER '+reference,27,700,'#526783')
        s.text(x+22,235,name,29,600);s.text(x+22,281,claim,25);s.text(x+22,323,'Sinistre : '+date,22)
        s.line(x+22,355,x+412,355)
        s.text(x+22,404,'COMPTE DE REMBOURSEMENT',17,color='#7c8793')
        s.text(x+22,449,'LU•• •••• •••• •••• 7849',23,600)
        s.text(x+22,537,'Pièce bancaire jointe',21,color='#7c8793')
    s.text(35,621,'Vue de consultation · coordonnées masquées',18,color='#7c8793')
    s.save()
    s=Sheet('case-06-b.svg',900,830,'#fcfbf7')
    s.text(54,71,'SERVICES BANCAIRES',25,700,'#4b575d')
    s.line(54,104,846,104,'#4b575d')
    s.text(54,169,'ATTESTATION DE COMPTE',36,700)
    s.text(54,221,'Émise le 02 novembre 2026',23,color='#788285')
    s.text(54,294,'Nous attestons que les personnes désignées ci-dessous',25)
    s.text(54,333,'sont cotitulaires du compte indiqué sur cette attestation.',25)
    s.field(54,411,'TITULAIRES','Alex Martin et Charlie Martin',792)
    s.field(54,515,'TYPE DE COMPTE','Compte joint',792)
    s.field(54,619,'IBAN (MASQUÉ POUR LE JEU)','LU•• •••• •••• •••• 7849',792)
    s.text(54,756,'Document délivré à la demande des titulaires.',20,color='#788285')
    s.save()


def photo_record(name, source, date, reference):
    s=Sheet(name,900,720,'#f7f6f0')
    s.text(28,36,'PIÈCE JOINTE / '+reference,19,color='#747b80')
    s.text(28,83,'Sinistre survenu le '+date,30,600)
    encoded=base64.b64encode((OUT/source).read_bytes()).decode()
    s.parts.append(f'<image x="0" y="120" width="900" height="600" href="data:image/webp;base64,{encoded}"/>')
    # Photo cards keep all caption area above the actual photograph.
    (OUT/name).write_text('\n'.join(s.parts+['</g></svg>']))


if __name__ == '__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    report();declaration();garage_invoice();detailed_invoice();transfer();accounts()
    photo_record('case-05-a.svg','case-05-a.webp','12/10/2026','A-517')
    if (OUT/'case-05-b.webp').exists():
        photo_record('case-05-b.svg','case-05-b.webp','03/11/2026','A-862')
