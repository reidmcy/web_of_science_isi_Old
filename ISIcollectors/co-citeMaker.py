#Written by Reid McIlroy-Young for John McLevey
import os
import sys
import csv
import networkx as nx

#output file name
graphOutFile = "co-CiteNetwork.graphml"

#cutoff for edges to be written weight must be >= cutoff
cutoff = 0

#Type of file the script looks for
inputSuffix = ".txt"

class BadPaper(Warning):
    """
    Exception thrown by paperParser and isiParser for mis-formated papers
    """
    pass

def paperParser(paper):
    """
    paperParser reads paper until it reaches 'EF' for each field tag it adds an
    entry to the returned dict with the tag as the key and a list of the entries
    for the tag as the value, the list has each line as an entry.
    """
    tdict = {}
    currentTag = ''
    for l in paper:
        if 'ER' in l[:2]:
            return tdict
        elif '   ' in l[:3]: #the string is three spaces in row
            tdict[currentTag].append(l[3:-1])
        elif l[2] == ' ':
            currentTag = l[:2]
            tdict[currentTag] = [l[3:-1]]
        else:
            raise BadPaper("Field tag not formed correctly: " + l)
    raise BadPaper("End of file reached before EF")

def isiParser(isifile):
    """
    isiParser reads a file, checks that the header is correct then reads each
    paper returning a list of of dicts keyed with the field tags.
    """
    f = open(isifile, 'r')
    if "VR 1.0" not in f.readline() and "VR 1.0" not in f.readline():
        raise BadPaper(isifile + " Does not have a valid header")
    notEnd = True
    plst = []
    while notEnd:
        try:
            l = f.next()
        except StopIteration as e:
            raise BadPaper("File ends before EF found")
        if not l:
            raise BadPaper("No ER found in " + isifile)
        elif l.isspace():
            continue
        elif 'EF' in l[:2]:
            notEnd = False
            break
        else:
            try:
                if l[:2] != 'PT':
                    raise BadPaper("Paper does not start with PT tag")
                plst.append(paperParser(f))
                plst[-1][l[:2]] = l[3:-1]
            except Warning as w:
                raise BadPaper(str(w.message) + "In " + isifile)
            except Exception as e:
                 raise e
    try:
        f.next()
        print "EF not at end of " + isifile
    except StopIteration as e:
        pass
    finally:
        return plst

def getFiles(suffix):
    """
    getFiles reads the current directory and returns all files ending with
    suffix. Terminates the program if none are found, no exceptions thrown.
    """
    fls = sys.argv[1:] if sys.argv[1:] else [f for f in os.listdir(".") if f.endswith(suffix)]
    if len(fls) == 0:
        #checks for any valid files
        print "No " + suffix + " Files"
        sys.exit()
    else:
        #Tells how many files were found
        print str(len(fls)) + " files found."
    return fls

def getCoauths(f, grph):
    """
    getCoauths reads f with isiParser. Then reads the CR field if there are more
    than 1 entries it assigns an ID to each citation either author date or the
    full entry if it cannot do that. Then edges are constructed between each
    node or if edges exist their weight is incremented.
    Each node also has a val field that contains the additional information that
    citation has excluding DOI number, although DOI removal is not good.
    """
    plst = isiParser(f)
    for p in plst:
        if 'CR' in p and len(p['CR']) > 1:
            for i in range(len(p['CR'])):
                splitCit1 = p['CR'][i].split(', ')
                if len(splitCit1) > 1:
                    cId1 = splitCit1[0].replace(' ',' ').replace('.','').upper() + ' ' + splitCit1[1]
                else:
                    cId1 = p['CR'][i].upper()
                if not grph.has_node(cId1):
                    if len(splitCit1) < 3:
                        cExtra1 = ''
                    elif len(splitCit1[-1]) > 3 and 'DOI' in splitCit1[-1][:3].upper():
                        cExtra1 = ', '.join(splitCit1[2:-1])
                    else:
                        cExtra1 = ', '.join(splitCit1[2:])
                    grph.add_node(cId1, val = cExtra1)
                for j in range(i + 1, len(p['CR'])):
                    splitCit2 = p['CR'][j].split(', ')
                    if len(splitCit2) > 1:
                        cId2 = splitCit2[0].replace(' ',' ').replace('.','').upper() + ' ' + splitCit2[1]
                    else:
                        cId2 = p['CR'][j].upper()
                    if not grph.has_node(cId2):
                        if len(splitCit2) < 3:
                            cExtra2 = ''
                        elif len(splitCit2[-1]) > 3 and 'DOI ' in splitCit2[-1][:4].upper():
                            cExtra2 = ', '.join(splitCit2[2:-1])
                        else:
                            cExtra2 = ', '.join(splitCit2[2:])
                        grph.add_node(cId2, val = cExtra2)
                    if grph.has_edge(cId1, cId2):
                        grph.edge[cId1][cId2]['weight'] += 1
                    else:
                        grph.add_edge(cId1, cId2, weight = 1)

if __name__ == '__main__':
    if os.path.isfile(graphOutFile):
        #Checks if the output outputFile already exists and terminates if so
        print graphOutFile +  " already exists\nexisting"
        sys.exit()
        #os.remove(graphOutFile)
    flist = getFiles(inputSuffix)
    G = nx.Graph()
    for isi in flist:
        try:
            print "Reading " + isi
            getCoauths(isi, G)
        except BadPaper as b:
            print b
        except Exception, e:
            #If any exceptions are raised cleans up and prints them
            print 'Exception:'
            print e
            print "Deleting " + graphOutFile
            os.remove(graphOutFile)
    print "Trimming"
    for ed in G.edges():
            if G.edge[ed[0]][ed[1]]['weight'] <= cutoff:
                  G.remove_edge(ed[0],ed[1])
    print "Writing " + graphOutFile
    nx.write_graphml(G, graphOutFile)
    print "Done"
