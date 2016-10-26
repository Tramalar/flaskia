#!/usr/bin/python
# -*- coding: utf-8 -*-

import sqlite3
import os
import sys
import hashlib
from functools import wraps
from flask import Flask, session, redirect, url_for, escape, request, Response, render_template
from datetime import date
from dateutil.parser import parse
app = Flask(__name__)
app.secret_key='l\x04\\\xa6dO\xccSJ\x14\x1c\x8e\xd1\xb4\xa7\xa5\xe4\xbd6\xbb\x13\xb3\x92\x91'

con = sqlite3.connect(os.path.abspath('../../../kanta/video.sqlite'))
con.row_factory=sqlite3.Row

@app.route('/kirjaudu',methods=["POST","GET"])
def kirjaudu():
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
            if tunnus=="tiea218@foobar.example" and m.digest() == '\xb3z\reW\x08\xbe\xb4&\xa9\x86\xc0!\x12\x9bJ\xba&\x97>\x8c\xe6kzQn\x88x\r\xc8\x88\ncz8\xfa\xafn\xc0\xd1\x8d\xc0\x87!\x1a\xe3\xd9\xa6\xc3\x04^\x8f\x11\xcb\x03g\xd7\xc9\x87\rg\xc8Z\xfe':
                session['logged'] = "Y"
                return redirect(url_for('vuokrat'))
        except Exception as e:
            return str(e)
    return render_template('kirjaudu.html')


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
        SELECT Jasen.Nimi as jn, jasen.jasenid as jid, Elokuva.Nimi as en,  vuokrauspvm, palautuspvm
        FROM Vuokraus, Elokuva, Jasen
        WHERE Vuokraus.JasenId=Jasen.JasenId AND Elokuva.ElokuvaId=Vuokraus.ElokuvaId
        ORDER BY Jasen.Nimi, jasen.jasenid, vuokrauspvm;
        """)
    except Exception as e:
        return (str(e))
    lista=[]
    for rivi in cur:
        if(rivi['palautuspvm']):
            lista.append((rivi['jid'],rivi['jn'],rivi['en'],rivi['vuokrauspvm'],rivi['palautuspvm']))
        else:                       
            lista.append((rivi['jid'],rivi['jn'],rivi['en'],rivi['vuokrauspvm'],"-"))
    cur.close()
    return render_template("vuokrat.html",lista=lista)
   
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

@app.route('/elokuvat')
@auth
def elokuvat():
    try:
        cur=con.cursor()
        cur.execute("""
        SELECT Nimi, ElokuvaId, tyypinnimi as tn, julkaisuvuosi as jv,arvio ,vuokrahinta as vh
        FROM Elokuva, lajityyppi
        WHERE Elokuva.lajityyppiId=lajityyppi.lajityyppiId
        ORDER BY Nimi
        """)
    except Exception as e:
        return (str(e))
    lista=[]
    for rivi in cur:                
        lista.append((rivi['ElokuvaId'],"%s (%d), Genre: %s, Arvio: %d/10, vuokrahinta: %.1f euroa" %(rivi['Nimi'],rivi['jv'],rivi['tn'],rivi['arvio'],rivi['vh'])))
    cur.close()
    return render_template("elokuvat.html",lista=lista)
@app.route('/lisaa')
@auth
def lisaa():
    if ('vvirhe' in request.args):
        vvirhe = request.args['vvirhe']=='True'
    else:
        vvirhe=False
    if ('pvirhe' in request.args):
        pvirhe = request.args['pvirhe']=='True'
    else:
        pvirhe=False
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
    
    return render_template("lisaa.html",listaE=listaE,listaJ=listaJ,vvirhe=vvirhe,pvirhe=pvirhe)

@app.route('/lisaaelokuva')
@auth   
def lisaaelokuva():
    if(len(request.args)):
        virhe= 'True'==request.args['virhe']
        avirhe='True'==request.args['avirhe']
        hvirhe='True'==request.args['hvirhe']
        vvirhe='True'==request.args['vvirhe']
    else:
        virhe=False
        avirhe=False
        hvirhe=False
        vvirhe=False
    listaG=haeGenret()
    return render_template("lisaaleffa.html",listaG=listaG,virhe=virhe,avirhe=avirhe,hvirhe=hvirhe,vvirhe=vvirhe)

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
   
@app.route('/leffanlisays', methods=["POST"])
@auth
def leffanlisays(): 
    gid= request.form.get("genre")
    elokuva= request.form.get("leffa")
    arvio=request.form.get("arvio")
    hinta=request.form.get("hinta")
    vuosi=request.form.get("vuosi")

    virhe=elokuva==""
    avirhe=arvio==""
    hvirhe=hinta==""
    vvirhe=vuosi==""
    if(virhe or avirhe or hvirhe or vvirhe):
        return redirect(url_for('lisaaelokuva',virhe=virhe,avirhe=avirhe,hvirhe=hvirhe,vvirhe=vvirhe))
    
  
    try:
        con.execute("""
        INSERT INTO Elokuva (Nimi, LajityyppiId, Vuokrahinta, Arvio, Julkaisuvuosi)
        VALUES ( :elokuva, :genre, :hinta, :arvio, :vuosi)
        """, {"elokuva": elokuva,"genre": int(gid), "hinta": float(hinta),"arvio":int(arvio),"vuosi":int(vuosi)})  
        con.commit()
    except Exception as e:
        return str(e)
    
    return redirect(url_for('elokuvat'))

@app.route('/lisays', methods=["POST"])
@auth
def lisays(): 
    jid= request.form.get("jasen")
    eid= request.form.get("leffa")
    vpv= request.form.get("vuokraus")
    ppv= request.form.get("palautus") 
    if(str(vpv)==""):
        return redirect(url_for('lisaa', vvirhe=True))
    try:
        vuokpaiv=parse(vpv).date()
    except ValueError:
        return redirect(url_for('lisaa', vvirhe=True))
        
    if(str(ppv)==""):
        try:
            con.execute("""
            INSERT INTO Vuokraus (JasenId,ElokuvaId,vuokrauspvm)
            VALUES (:jasenid, :elokuva, :vuokraus)
            """, {"jasenid": int(jid), "elokuva": int(eid),"vuokraus": vuokpaiv})  
            con.commit()
        except Exception as e:
            return str(e)
    else:
        try:
            try:
                palpaiv=parse(ppv).date()
            except ValueError:
                return redirect(url_for('lisaa', pvirhe=True))
            if(palpaiv < vuokpaiv):
                return redirect(url_for('lisaa',pvirhe=True))     
            con.execute("""
            INSERT INTO Vuokraus (JasenId,ElokuvaId,vuokrauspvm,palautuspvm)
            VALUES (:jasenid, :elokuva, :vuokraus, :palautus )
            """, {"jasenid": int(jid), "elokuva": int(eid),"vuokraus": vuokpaiv, "palautus": palpaiv})   
            con.commit()
        except Exception as e:
            return str(e)
    return redirect(url_for('vuokrat'))
    
if __name__ == '__main__':
    app.debug = True
    app.run(debug=True)