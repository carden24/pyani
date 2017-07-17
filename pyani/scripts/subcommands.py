#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""subcommands.py

Provides subcommand functions for the pyani.py script

- download:      download assemblies from NCBI
- classify:      classify ANI results

The code in this module should mediate between the user via CLI and the actual
'lifting' code in the pyani module - it should not be implementing
calculations.

(c) The James Hutton Institute 2017
Author: Leighton Pritchard
Contact: leighton.pritchard@hutton.ac.uk
Leighton Pritchard,
Information and Computing Sciences,
James Hutton Institute,
Errol Road,
Invergowrie,
Dundee,
DD6 9LH,
Scotland,
UK

The MIT License

Copyright (c) 2017 The James Hutton Institute
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import os

from collections import namedtuple

from .. import __version__, download, pyani_tools
#from . import tools


# Download sequence/class/label data from NCBI
def subcmd_download(args, logger):
    """Download all assembled genomes beneath a passed taxon ID from NCBI."""
    # Create output directory
    pyani_tools.make_outdir(args.outdir, args.force, args.noclobber, logger)
    
    # Set Entrez email
    download.set_ncbi_email(args.email)
    logger.info("Setting Entrez email address: %s", args.email)
    
    # Get list of taxon IDs to download
    taxon_ids = download.split_taxa(args.taxon)
    logger.info("Taxon IDs received: %s", taxon_ids)

    # Get assembly UIDs for each taxon
    asm_dict = pyani_tools.make_asm_dict(taxon_ids, args.retries)
    for tid, uids in asm_dict.items():
        logger.info("Taxon ID summary\n\tQuery: " +\
                    "%s\n\tasm count: %s\n\tUIDs: %s", tid, len(uids), uids)


    # Compile list of outputs for class and label files, and a list of
    # skipped downloads (and a helper tuple for collating skipped genome
    # information)
    classes = []
    labels = []
    skippedlist = []
    Skipped = namedtuple("Skipped",
                         "taxon_id accession organism strain " +
                         "url")

    # Download contigs and hashes for each assembly UID
    for tid, uids in asm_dict.items():
        logger.info("Downloading contigs for Taxon ID %s", tid)
        for uid in uids:
            # Obtain eSummary            
            logger.info("Get eSummary information for UID %s", uid)
            esummary, filestem = download.get_ncbi_esummary(uid, args.retries)
            uid_class = download.get_ncbi_classification(esummary)

            # Report summary
            outstr = '\n\t'.join(["Taxid: %s" % esummary['SpeciesTaxid'],
                                  "Accession: %s" %
                                  esummary['AssemblyAccession'],
                                  "Name: %s" % esummary['AssemblyName'],
                                  "Organism: %s" % uid_class.organism,
                                  "Genus: %s" % uid_class.genus,
                                  "Species: %s" % uid_class.species,
                                  "Strain: %s" % uid_class.strain])
            logger.info("eSummary information:\n\t%s", outstr)

            # Make label/class text
            labeltxt, classtxt = download.create_labels(uid_class, filestem)
            classes.append(classtxt)
            labels.append(labeltxt)
            logger.info("Label and class file entries\n" + 
                        "\tLabel: %s\n\tClass: %s", labeltxt, classtxt)
    
            # Obtain URLs
            ftpstem="ftp://ftp.ncbi.nlm.nih.gov/genomes/all"
            suffix="genomic.fna.gz"
            logger.info("Retrieving URLs for %s", filestem)
            dlstatus = pyani_tools.download_genome_and_hash(filestem, suffix,
                                                            ftpstem,
                                                            args.outdir,
                                                            args.timeout,
                                                            logger)
            if dlstatus.skipped:
                skippedlist.append(Skipped(tid, uid,
                                           uid_class.organism,
                                           uid_class.strain,
                                           dlstatus.url))
                continue  # Move straight on to the next download

            # Report the working download
            logger.info("Downloaded from URL: %s", dlstatus.url)
            logger.info("Wrote assembly to: %s", dlstatus.outfname)
            logger.info("Wrote MD5 hashes to: %s", dlstatus.outfhash)

            # Check hash for the download
            hashstatus = download.check_hash(dlstatus.outfname,
                                             dlstatus.outfhash)
            logger.info("Local MD5 hash: %s", hashstatus.localhash)
            logger.info("NCBI MD5 hash: %s", hashstatus.filehash)
            if hashstatus.passed:
                logger.info("MD5 hash check passed")
            else:
                logger.warning("MD5 hash check failed.")

            # Extract downloaded files
            ename = os.path.splitext(dlstatus.outfname)[0]
            if os.path.exists(ename) and args.noclobber:
                logger.warning("Output file %s exists, not extracting", ename)
            else:
                logger.info("Extracting archive %s to %s",
                            dlstatus.outfname, ename)
                download.extract_contigs(dlstatus.outfname, ename)
        
    # Write class and label files
    pyani_tools.write_classes_labels(classes, labels, args.outdir,
                                     args.classfname,
                                     args.labelfname, args.noclobber, logger)

    # Show skipped genome list
    if len(skippedlist):
        logger.warning("%d genome downloads were skipped", len(skippedlist))
        for skipped in skippedlist:
            outstr = '\n\t'.join(["taxon id: %s" % skipped.taxon_id,
                                   "accession: %s" % skipped.accession,
                                   "URL: %s" % skipped.url])
            logger.warning("%s %s:\n\t%s", skipped.organism, skipped.strain,
                           outstr)


# Generate MD5 hashes for each genome in an input directory
def subcmd_index(args, logger):
    """Generate an MD5 hash for each genome in an input directory.

    Identify the genome files in the input directory, and generate a single
    MD5 for each so that <genome>.fna produces <genome>.md5
    """
    raise NotImplementedError


def subcmd_db(args, logger):
    """Perform operations on the SQLite3 database containing analysis info.

    - set the current database associated with this analysis
    - create the database if it does not exist
    - update a database with existing pyani results
    - merge two or more databases
    """
    raise NotImplementedError


def subcmd_anim(args, logger):
    """Perform ANIm on all genome files in an input directory.
    """
    raise NotImplementedError


def subcmd_anib(args, logger):
    """Perform ANIm on all genome files in an input directory.
    """
    raise NotImplementedError


def subcmd_aniblastall(args, logger):
    """Perform ANIm on all genome files in an input directory.
    """
    raise NotImplementedError


def subcmd_render(args, logger):
    """Visualise ANI results for an analysis.
    """
    raise NotImplementedError
            
# Classify input genomes on basis of ANI coverage and identity output
def subcmd_classify(args, logger):
    """Take pyani output, and generate of classifications of the input data.
    """
    raise NotImplementedError
