#!/usr/bin/env python

#
# Zerg - simple ERG/MRC -> Zwift Workout File convertor
#
# This is a deliberately simple, self-contained script to avoid any complications
# with using external libraries, whether standard (e.g. shlex) or 3rd party (e.g.
# PLY, pyparsing). As such, and also because it's had to be wipped up inbetween
# actually working on other code, it's a bit shonky and decidely odd-looking in
# places... but it may help someone do a couple of simple conversions if they're
# not fussy.
#
# Copyright (c) 2015 Tim Parker
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons
# to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
# BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

import os, sys, re
import xml.etree.ElementTree as XmlDoc
import xml.dom.minidom as MiniDom

class ErgParser :
    # sectionStartRe = re.compile( '\[(?P<tag>.*?)\]' )
    sectionStartRe = re.compile( '[[](?P<tag>[^]]+)[]].*' )
    sectionEndRe = re.compile( '[[]END (?P<tag>[^]]+)[]].*' )

    def __init__( self, path, fileOutput = None, fileType = None, outputDir = None, skipCourseText = None ) :
        self.fileType = fileType
        self.input = path
        self.output = fileOutput
        self.outputDir = outputDir
        self.rootNode = XmlDoc.Element( 'workout_file' )
        self.currentNode = self.rootNode
        self.skipCourseText = skipCourseText

        self.sectionTokens = {
            'COURSE HEADER' : ( self.headerStart, self.headerParse, self.headerEnd ) ,
            'COURSE DATA' : ( self.dataStart, self.dataParse, self.dataEnd ) ,
            'COURSE TEXT' : ( self.textStart, self.textParse, self.textEnd )
        }

        self.parsers = [ self.startOfSection ]
        self.parse( self.input )

    def write( self ) :
        if not self.output :
            stem, ext = os.path.splitext( self.input )
            self.output = '%s.zwo' % stem
            if self.outputDir :
                self.output = os.path.join( self.outputDir, os.path.basename( self.output ) )
        try :
            strm = open( self.output, 'w' )
            strm.write( '%s\n' % MiniDom.parseString( XmlDoc.tostring( self.rootNode, 'utf-8')
                                   ).toprettyxml(indent="    ") )
            strm.close()
        except Exception as err :
            raise Exception( "Error writing output file %s : " % ( outputFile, err ) )

    def parser( self ) :
        return self.parsers[-1]

    def startOfSection( self, line ) :
        match = self.sectionStartRe.match( line )
        if match :
            start, parse, _ = self.sectionTokens[ match.group( 'tag' ) ]
            start()
            self.parsers.append( parse )
            return True
        return False

    def endOfSection( self, line ) :
        match = self.sectionEndRe.match( line )
        if match :
            _, _, end = self.sectionTokens[ match.group( 'tag' ) ]
            end()
            self.parsers.pop()
            return True
        return False

    def power( self, percent ) :
        # Hard-coded for percentage FTP for now (e.g. MRC files)
        # Zwift uses decimal FTP ratio
        return percent / 100

    def duration( self, mins ) :
        # Hard-coded for input interval times in minutes (ERG/MRC)
        # Zwift uses seconds (single in file, 5 sec rounding in GUI)
        return round(60 * mins, 0)

    def addInterval( self, intervalType, mins, powerLow, powerHigh ) :
        # NB. duration is minutes in ERG/MRC for data, and seconds for Zwift
        # workout files (and also time offset for text events in ERG/MRC).
        return XmlDoc.SubElement(
            self.currentNode, intervalType, Duration = "%s" % self.duration( mins ) ,
            PowerLow = '%.3f' % self.power( powerLow ), PowerHigh = '%.3f' % self.power( powerHigh ) )

    def addNode( self, name, value, parent = None ) :
        if not parent : parent = self.currentNode
        node = XmlDoc.SubElement( parent, name )
        node.text = value
        return node

    def addText( self, interval, timeOffset, message):
        # Iterate through all nodes in workout and add text when needed
        periodStart = 0.0
        periodEnd = 0.0
        for child in self.rootNode.find('workout'):
            periodEnd += float(child.attrib['Duration'])

            if (interval >= periodStart) & (interval < periodEnd):
                XmlDoc.SubElement( child, 'textevent', message = message, timeoffset = "%f" % timeOffset )
                break

            periodStart = periodEnd
        pass

    #-----------------------------
    # Course Header
    #-----------------------------
    def headerStart( self ) : pass
    def headerEnd( self ) : pass

    def headerParse( self, line ) :
        headerTokens = {
            'FILE NAME' : 'name' ,
            'DESCRIPTION' : 'description'
        }
        if not self.endOfSection( line ) :
            tokens = line.split( '=' )
            if len( tokens ) == 1 :
                # e..g. MINUTES PERCENT
                pass
            elif len( tokens ) == 2 :
                try :
                    # Use filename as Zwift name if input is 'none'
                    if tokens[0].strip() == 'FILE NAME' and tokens[1].strip() == 'none':
                        tokens[1] = os.path.splitext(os.path.basename(self.input))[0]
                    self.addNode( headerTokens[ tokens[0].strip() ], tokens[1].strip() )
                except Exception as err :
                    print("Muuuh : {0}".format(str(err)))
                    pass

    #-----------------------------
    # Course Data
    #-----------------------------
    def dataStart( self ) :
        self.data = []
        self.currentNode = XmlDoc.SubElement( self.rootNode, 'workout' )

    def dataEnd( self ) :
        if self.data :
            numPoints = len( self.data )
            print("Data points : %d" % numPoints)

            # numPoints == 1 is a special case (time datum must be non-negative)
            # Deal with that later,
            prevTime, prevEffort = self.data[0]
            for currTime, currEffort in self.data[1:] :
                duration = currTime - prevTime
                deltaEffort = currEffort - prevEffort
                print("Duration = %.3f, start = %.3f, end = %.3f (D = %.3f)" % (
                    duration, prevEffort, currEffort, deltaEffort ))


                if duration :
                    # Increasing effort is 'Warmup' in Zwift parlance, decreasing effort
                    # is 'Cooldown' and no change is 'SteadyState' (note case).
                    intervalType = 'SteadyState'
                    if   deltaEffort > 0 : intervalType = 'Warmup'
                    elif deltaEffort < 0 : intervalType = 'Cooldown'

                    interval = self.addInterval( intervalType, duration, prevEffort, currEffort )

                # .. and around we go again
                prevTime = currTime
                prevEffort = currEffort

        del self.data

    def dataParse( self, line ) :
        if not self.endOfSection( line ) :
            #print '%s' % line
            try :
                mins, percent = map( float, line.split()[0:2] )
                self.data.append( ( mins, percent ) )
            except :
                pass

    #-----------------------------
    # Course Text (TBD)
    #-----------------------------
    def textStart( self ) : pass
    def textEnd( self ) : pass
    def textParse( self, line ) :
        # print('%s' % line)
        if not self.endOfSection( line ) :
            if not self.skipCourseText :
                tokens = re.split(r'\t+', line.rstrip())
                if len (tokens) == 8 :
                    interval = float(tokens[0])
                    message = tokens[1]
                    timeOffset = float(tokens[7])
                    # print('%s (at %s + %s)' % (message, interval, timeOffset))

                    self.addText(interval, timeOffset, message)
        pass


    def parse( self, path ) :
        try :
            for line in open( path ) :
                print("Parser '%s', line : %s" % ( self.parser(), line ))
                self.parser()( line )

        except Exception as err :
            print('Muuuh : %s' % err)
        finally :
            self.write()

#---------------------------------------------------------
# Mainline - options parsing and drivers
#---------------------------------------------------------
if __name__ == '__main__' :
    import getopt

    def printUsage() :
        print("""
        zerg [options] file1.mrc [file2.mrc ...]

        Convert one or more ERG/MRC files to Zwift Workout (zwo) files.
        Currently only MRC files are supported (workouts are relative to
        FTP, effort is NOT defined in Watts).

        Options :

        -D <dir>  Place all converted files into directory <dir>.
                  Default is to write the converted data file to
                  the same directory as the original data file.

        -h        Help. Show this page and exit.

        -o <name> Save converted file to <name>. Default is to
                  name the converted data file the same as the
                  original data file except for the extension
                  which will be changed to '.zwo', e.g.

                       example.mrc -> example.zwo

                  This obviously only makes sense when one file
                  is being converted. No check is made that the
                  converted data file name is different from the
                  original data file name currently - beware.

        -m        Skip Course Text conversion.

        """)


    optFileType = None
    optFileOutput = None
    optOutputDir = None
    optSkipCourseText = None

    fileTypes = {
        'erg' : ( 'ERG file', 'WATTS' ) ,
        'mrc' : ( 'MRC file', 'PERCENT' )
        }

    try :
        opts, files = getopt.getopt( sys.argv[1:], "D:ho:t:m" )

    except getopt.GetoptError as msg :
        print("Invalid option(s) : %s" % msg)
        printUsage()
        sys.exit( 1 )

    except Exception as err :
        print("Internal error, exiting : %s" % err)
        sys.exit( 2 )

    else :
        for opt, val in opts :
            if opt == '-D' :
                optOutputDir = val
            elif opt == '-h' :
                printUsage()
                sys.exit( 0 )
            elif opt == '-o' :
                optFileOutput = val
            elif opt == '-t' :
                try :
                    desc, _ = fileTypes[ val ]
                    print("Forcing file type to '%s' (%s)" % ( val, desc ))
                    optFileType = val
                except :
                    print("Invalid file type '%s', should be one of %s" % (
                        val, ', '.join( fileTypes.keys() ) ))
                    sys.exit( 3 )
            elif opt == "-m" :
                optSkipCourseText = True

        for path in files :
            ErgParser( path,
                       fileType = optFileType, fileOutput = optFileOutput, outputDir = optOutputDir, skipCourseText =  optSkipCourseText)
