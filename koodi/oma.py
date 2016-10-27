#!/usr/bin/python
# -*- coding: utf-8 -*-

import sqlite3
import os
import sys
import hashlib
from functools import wraps
from flask import Flask, session, redirect, url_for, escape, request, Response, render_template
from datetime import date, datetime
from dateutil.parser import parse
app = Flask(__name__)
app.secret_key='l\x04\\\xa6dO\xccSJ\x14\x1c\x8e\xd1\xb4\xa7\xa5\xe4\xbd6\xbb\x13\xb3\x92\x91'

con = sqlite3.connect(os.path.abspath('../../../kanta/video.sqlite'))
con.row_factory=sqlite3.Row

@app.route('/kirjaudu',methods=["POST","GET"])
def kirjaudu():
    virhe=("","")
    if(request.method=="POST"):
        try:
            m = hashlib.sha512()
            tunnus=""
            if(request.form.get('tunnus')):
                tunnus=request.form.get('tunnus')
            salasana=""
            if(request.form.get('salasana')):
                salasana=request.form.get('salasana')
            m.update(salasana)
            if tunnus=="tiea218@foobar.example":
                if m.digest() == '\xb3z\reW\x08\xbe\xb4&\xa9\x86\xc0!\x12\x9bJ\xba&\x97>\x8c\xe6kzQn\x88x\r\xc8\x88\ncz8\xfa\xafn\xc0\xd1\x8d\xc0\x87!\x1a\xe3\xd9\xa6\xc3\x04^\x8f\x11\xcb\x03g\xd7\xc9\x87\rg\xc8Z\xfe':
                    session['logged'] = "Y"
                    return redirect(url_for('vuokrat'))
                else:
                    virhe=('',unicode('Väärä salasana',"UTF-8"))
            else:
                virhe=(unicode('Tunnusta ei löydy',"UTF-8"),'')
        except Exception as e:
            return str(e)
    return render_template('kirjaudu.html', virhe=virhe)


def auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not 'logged' in session:
            return redirect(url_for('kirjaudu'))
        return f(*args, **kwargs)
    return decorated
    
@app.route('/ulos',methods=["POST","GET"])
@auth
def kirjauduUlos():
    if(request.method=="POST"):
        try:        
            session.pop('logged', "")
            con.close()
            return redirect(url_for('kirjaudu'))
        except Exception as e:
            return str(e)
    return render_template('ulos.html')

@app.route('/')
@auth
def vuokrat():
    try:
        cur=con.cursor()
        cur.execute("""
        SELECT jasenid as jid, nimi as jn
        FROM Jasen
        ORDER BY nimi, jasenid;
        """)
        jasenet=[]
        for rivi in cur:
            jasenet.append( (rivi['jn'],rivi['jid']) )
        jasenenvuokrat=[]
        for (jasen,id) in jasenet:
            vuokrat=[]
            cur.execute("""
            SELECT Elokuva.Nimi as en,  vuokrauspvm, palautuspvm
            FROM Vuokraus, Elokuva
            WHERE Vuokraus.JasenId= ?  AND Elokuva.ElokuvaId=Vuokraus.ElokuvaId
            ORDER BY vuokrauspvm;
            """,(id,))
            for rivi in cur:
                if rivi['palautuspvm']:
                    vuokrat.append((rivi['en'], rivi['vuokrauspvm'],rivi['palautuspvm']))
                else:
                    vuokrat.append((rivi['en'], rivi['vuokrauspvm'],"-"))
            jasenenvuokrat.append((jasen,vuokrat))
        cur.close()
    except Exception as e:
        return (str(e))
    return render_template("vuokrat.html",lista=jasenenvuokrat)
   
@app.route('/lisaa', methods=["POST", "GET"])
@auth
def lisaa():
    cur=con.cursor()
    cur.execute("""
    SELECT Nimi, JasenId
    FROM Jasen
    """)
    listaJ=[]
    for rivi in cur:
        listaJ.append((rivi['Nimi'],rivi['JasenId']))
    cur.execute("""
    SELECT Nimi, ElokuvaId
    FROM Elokuva
    """)
    listaE=[]
    for rivi in cur:
        listaE.append((rivi['Nimi'],rivi['ElokuvaId']))
    
    virhe=("","","")
    if(request.method=="POST"):
        onnistui=True
        virhe=lisays(request.form)
        for i in virhe:
            if i:
                onnistui=False
                break;
        if(onnistui):   
            return redirect(url_for('vuokrat'))
    return render_template("lisaa.html",listaE=listaE,listaJ=listaJ,vvirhe=virhe[0],pvirhe=virhe[1],lvirhe=virhe[2])
 


def lisays(lomake): 
    jid= lomake.get("jasen")
    eid= lomake.get("leffa")
    vpv= lomake.get("vuokraus")
    ppv= lomake.get("palautus") 
    if(str(vpv)==""):
        return ("Anna vuokrauspvm","","")
    try:
        vuokpaiv=parse(vpv).date()
    except ValueError:
        return ("Virheellinen pvm","","")
    tanaan=date.today()
    if(vuokpaiv<tanaan):
        return ("Antamasi vuokrauspvm on jo mennyt ohi","","")
        
        
    if(str(ppv)==""):
        try:
            con.execute("""
            INSERT INTO Vuokraus (JasenId,ElokuvaId,vuokrauspvm)
            VALUES (:jasenid, :elokuva, :vuokraus)
            """, {"jasenid": int(jid), "elokuva": int(eid),"vuokraus": vuokpaiv})  
            con.commit()
        except:
            return ("","","Virhe datan siirrossa tietokantaan")
    else:
        try:
            try:
                palpaiv=parse(ppv).date()
            except ValueError:
                return ("","Virheellinen pvm","")
            if(palpaiv < vuokpaiv):
                return ("","Palautuspvm ei voi olla ennen vuokrausta","")
            con.execute("""
            INSERT INTO Vuokraus (JasenId,ElokuvaId,vuokrauspvm,palautuspvm)
            VALUES (:jasenid, :elokuva, :vuokraus, :palautus )
            """, {"jasenid": int(jid), "elokuva": int(eid),"vuokraus": vuokpaiv, "palautus": palpaiv})   
            con.commit()
        except:
            return ("","","Virhe datan siirrossa tietokantaan")
    return ("","","")
  
@app.route('/elokuvat', methods=["POST","GET"])
@auth
def elokuvat():
    try:
        if (request.method=="POST"):
            id= request.form.get('tunniste')
            jarj= request.form.get('jarjestys')
            con.execute("""
            DELETE FROM Elokuva
            WHERE ElokuvaId= ? ;
            """,(int(id),))
            con.commit()
            return redirect(url_for('elokuvat',jarjestys=jarj))
    except Exception as e:
        return str(e)
    jarjesta="Nimi"
    if(len(request.args)):
        jarjesta=request.args['jarjestys']   
    try:
        cur=con.cursor()
        if(jarjesta=="Nimi"):
            cur.execute("""
            SELECT Nimi, elokuva.ElokuvaId, tyypinnimi as tn, julkaisuvuosi as jv,arvio ,vuokrahinta as vh, count(vuokraus.elokuvaid) as lkm
            FROM Elokuva, lajityyppi
            LEFT JOIN vuokraus ON elokuva.elokuvaid=vuokraus.elokuvaid
            WHERE Elokuva.lajityyppiId=lajityyppi.lajityyppiId
            GROUP BY elokuva.elokuvaid
            ORDER BY Nimi""")
        if(jarjesta=="lkm"):
            cur.execute("""
            SELECT Nimi, elokuva.ElokuvaId, tyypinnimi as tn, julkaisuvuosi as jv,arvio ,vuokrahinta as vh, count(vuokraus.elokuvaid) as lkm
            FROM Elokuva, lajityyppi
            LEFT JOIN vuokraus ON elokuva.elokuvaid=vuokraus.elokuvaid
            WHERE Elokuva.lajityyppiId=lajityyppi.lajityyppiId
            GROUP BY elokuva.elokuvaid
            ORDER BY lkm""")
        if(jarjesta=="jv"):
            cur.execute("""
            SELECT Nimi, elokuva.ElokuvaId, tyypinnimi as tn, julkaisuvuosi as jv,arvio ,vuokrahinta as vh, count(vuokraus.elokuvaid) as lkm
            FROM Elokuva, lajityyppi
            LEFT JOIN vuokraus ON elokuva.elokuvaid=vuokraus.elokuvaid
            WHERE Elokuva.lajityyppiId=lajityyppi.lajityyppiId
            GROUP BY elokuva.elokuvaid
            ORDER BY jv""")
        if(jarjesta=="arvio"):
            cur.execute("""
            SELECT Nimi, elokuva.ElokuvaId, tyypinnimi as tn, julkaisuvuosi as jv,arvio ,vuokrahinta as vh, count(vuokraus.elokuvaid) as lkm
            FROM Elokuva, lajityyppi
            LEFT JOIN vuokraus ON elokuva.elokuvaid=vuokraus.elokuvaid
            WHERE Elokuva.lajityyppiId=lajityyppi.lajityyppiId
            GROUP BY elokuva.elokuvaid
            ORDER BY arvio""")
    except Exception as e:
        return (str(e))
    lista=[]
    for rivi in cur:       
        lkm=rivi['lkm'] 
        lista.append((lkm,jarjesta,rivi['ElokuvaId'],"%s (%d), Genre: %s, Arvio: %d/10, vuokrahinta: %.1f euroa, vuokrauksia: %d" %(rivi['Nimi'],rivi['jv'],rivi['tn'],rivi['arvio'],rivi['vh'],lkm)))
    cur.close()
    return render_template("elokuvat.html",lista=lista)
  
@app.route('/muokkaus/<id>')
@auth
def muokkaus(id):
    try:
        cur=con.cursor()
        cur.execute("""
        SELECT Nimi, tyypinnimi as tn, julkaisuvuosi as jv,arvio ,vuokrahinta as vh
        FROM Elokuva, lajityyppi
        WHERE Elokuva.lajityyppiId=lajityyppi.lajityyppiId AND Elokuva.ElokuvaId = ?
        """,(int(id),))
    except Exception as e:
        return (str(e))
    rivi=cur.fetchone()
    tiedot=((rivi['Nimi'],rivi['jv'],rivi['arvio'],rivi['vh'],rivi['tn'], int(id)))
    cur.close()
    return render_template('muokkaaleffaa.html',rivi=tiedot, listaG=haeGenret())

@app.route('/muokkaa',methods=["POST"])
@auth
def muokkaa():
    gid= request.form.get("genre")
    elokuva= request.form.get("leffa")
    arvio=request.form.get("arvio")
    hinta=request.form.get("hinta")
    vuosi=request.form.get("vuosi")
    id=request.form.get("leffaId")
    try:
        cur=con.cursor()
        cur.execute("""
        SELECT Nimi, lajityyppiId as gid, julkaisuvuosi as jv, arvio ,vuokrahinta as vh
        FROM Elokuva
        WHERE ElokuvaId = ?
        """,(id,))
    except Exception as e:
        return (str(e))
    rivi=cur.fetchone()
    cur.close()
    if(elokuva==""):
        elokuva=rivi['Nimi']
        
    if(gid=="tyhja"):
        gid=rivi['gid']
        
    if(arvio==""):
        arvio=rivi['arvio']
    else:
        arvio= int(arvio)
        
    if(vuosi==""):
        vuosi=rivi['jv']
    else:
        vuosi= int(vuosi)

    if(hinta==""):
        hinta=rivi['vh']
    else:
        hinta= float(hinta)

    try:
        con.execute("""
        UPDATE Elokuva
        SET Nimi= ?, lajityyppiId= ?, julkaisuvuosi=?, arvio=?, vuokrahinta=?
        WHERE ElokuvaId = ?
        """,(elokuva, gid, vuosi, arvio, hinta, id))
        con.commit()
    except Exception as e:
        return (str(e))
    
    return redirect(url_for("elokuvat"))
 
    
@app.route('/lisaaelokuva',methods=["POST","GET"])
@auth   
def lisaaelokuva():
    listaG=haeGenret()
    virhe=(False,False,False,False,False)
    if(request.method=="POST"):
        onnistui=True
        virhe=leffanlisays(request.form)
        for i in virhe:
            if i:
                onnistui=False
                break
        if(onnistui):   
            return redirect(url_for('elokuvat'))
    
    return render_template("lisaaleffa.html",listaG=listaG,virhe=virhe[0],avirhe=virhe[1],hvirhe=virhe[2],vvirhe=virhe[3],lvirhe=virhe[4])
  

def leffanlisays(lomake): 
    gid= lomake.get("genre")
    elokuva= lomake.get("leffa")
    arvio=lomake.get("arvio")
    hinta=lomake.get("hinta")
    vuosi=lomake.get("vuosi")

    virhe=elokuva==""
    avirhe=arvio==""
    hvirhe=hinta==""
    vvirhe=vuosi==""
    if(virhe or avirhe or hvirhe or vvirhe):
        return (virhe,avirhe,hvirhe,vvirhe,False)
    
    try:
        con.execute("""
        INSERT INTO Elokuva (Nimi, LajityyppiId, Vuokrahinta, Arvio, Julkaisuvuosi)
        VALUES ( :elokuva, :genre, :hinta, :arvio, :vuosi)
        """, {"elokuva": elokuva,"genre": int(gid), "hinta": float(hinta),"arvio":int(arvio),"vuosi":int(vuosi)})  
        con.commit()
    except:
        return (False,False,False,False,True)
    
    return (False,False,False,False,False)

def haeGenret():
    cur=con.cursor()
    cur.execute("""
    SELECT tyypinnimi, lajityyppiId
    FROM lajityyppi
    """)
    listaG=[]
    for rivi in cur:
        listaG.append((rivi['tyypinnimi'],rivi['lajityyppiId']))
    cur.close()
    return listaG
 
if __name__ == '__main__':
    app.debug = True
    app.run(debug=True)