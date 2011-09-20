# -*- coding: utf-8 -*-
"""Utils for importation of contacts"""
import csv
from datetime import datetime

import xlrd
import vobject

from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.db import connection

from tagging.models import Tag

from emencia.django.newsletter.models import Contact
from emencia.django.newsletter.models import MailingList

# defines possible columns name
# get_column method => maps column name to a correct contact field (otherwise return empty string)
COLUMNS_EXCEL = ['email', 'first_name', 'last_name', 'tags']
COLUMNS = {'email':['email','mail','e-mail'], 'first_name':['firstname','first name','first_name','prenom'], 'last_name':['lastname','last name','last_name','nom']} #, 'tags':['tags','tag','keyword']}
csv.register_dialect('edn', delimiter=';')

def get_column(fieldname):
    if fieldname in COLUMNS.keys():
        return fieldname
    else:
        for column in COLUMNS.keys():
            if fieldname.lower() in [ i.lower() for i in COLUMNS[column]]:
                return column

    return ''
csv.register_dialect('edn', delimiter=';')


def create_contact(contact_dict, workgroups=[], mailing_list=None, now=None):
    """Create a contact and validate the mail"""
    contact_dict['email'] = contact_dict['email'].strip()
    try:
        validate_email(contact_dict['email'])
        contact_dict['valid'] = 1
    except ValidationError:
        contact_dict['valid'] = 0

    # initialize boolean fileds ourselves to prevent sql warnings during LOAD DATA INFILE
    contact_dict['tester'] = 0
    contact_dict['subscriber'] = 1

    # when dealing withs thousands of entries we simply cannot create objects one at a time
    # so we should use a BulkInsert instead
    # extends contact infos with its possible relationship
    if workgroups:
        contact_dict['contacts'] = workgroups
    if mailing_list:
        contact_dict['mailinglist_subscriber'] = {'name':mailing_list.name,'description':mailing_list.description}
        #contact_dict['mailinglist_subscriber'] = mailing_list
    Contact.objects.bulk_insert( now, False, True, **contact_dict)
    return True

    # get_or_create is not appropriate for us as we cannot have unique email
    #contact, created = Contact.objects.get_or_create(
        #email=contact_dict['email'],
        #defaults=contact_dict)

    #if not created:
        #new_tags = contact_dict.get('tags')
        #if new_tags:
            #Tag.objects.update_tags(contact, '%s, %s' % (contact.tags, new_tags))

    #for workgroup in workgroups:
        #workgroup.contacts.add(contact)

    #return contact, created


def create_contacts(contact_dicts, mailing_name, importer_description, workgroups=[]):
    """Create all the contacts to import and
    associated them in a mailing list"""
    inserted = 0
    when = str(datetime.now()).split('.')[0]
    mailing_list = MailingList(
        name="%s" % mailing_name,
        description=_('Contacts imported by %s.') % importer_description)
    # do not save object otherwise it will have a primary key
    #mailing_list.save()

    for workgroup in workgroups:
        workgroup.mailinglists.add(mailing_list)

    # when dealing withs thousands of entries we simply cannot create objects one at a time
    # so we should use a BulkInsert instead
    myNow = datetime.now()
    for contact_dict in contact_dicts:
        created = create_contact( contact_dict, workgroups, mailing_list, myNow)
        #contact, created = create_contact(contact_dict, workgroups)
        #mailing_list.subscribers.add(contact)
        inserted += int(created)

    Contact.objects.bulk_insert_commit()
    #print connection.queries

    return inserted


def vcard_contacts_import(stream, mailing_name, workgroups=[] ):
    """Import contacts from a VCard file"""
    contacts = []
    vcards = vobject.readComponents(stream)

    for vcard in vcards:
        contact = {'email': vcard.email.value,
                   'first_name': vcard.n.value.given,
                   'last_name': vcard.n.value.family}
        contacts.append(contact)

    return create_contacts(contacts, mailing_name, 'vcard', workgroups)


def text_contacts_import(stream, mailing_name, workgroups=[] ):
    """Import contact from a plaintext file, like CSV"""
    contacts = []

    # use below trick to be ptyhon 2.5 compatible 
    # instead we should do contact_reader.fieldnames
    fieldnames = csv.reader(stream).next() 
    stream.seek(0)
    import_description = u'CSV\n Fichier : %s\n Champs : %s' % ( stream.name, fieldnames)

    contact_reader = csv.DictReader(stream, dialect='edn')
    for contact_row in contact_reader:
        contact = {}
        extra = ''
        for fieldname in contact_row:
            column = get_column(fieldname)
            if column != '':
                contact[column] = contact_row[fieldname]
            else:
                extra += '"' + fieldname+ '=' + contact_row[fieldname] + '" '
        contact['extra']=extra
        contacts.append(contact)

        #for i in range(len(contact_row)):
            #contact[COLUMNS[i]] = contact_row[i]
        #contacts.append(contact)

    return create_contacts(contacts, mailing_name, import_description, workgroups)


def excel_contacts_import(stream, mailing_name, workgroups=[] ):
    """Import contacts from an Excel file"""
    contacts = []
    wb = xlrd.open_workbook(file_contents=stream.read())
    sh = wb.sheet_by_index(0)

    for row in range(sh.nrows):
        contact = {}
        for i in range(len(COLUMNS_EXCEL)):
            try:
                value = sh.cell(row, i).value
                contact[COLUMNS_EXCEL[i]] = value
            except IndexError:
                break
        contacts.append(contact)

    return create_contacts(contacts, mailing_name, 'excel', workgroups)


def import_dispatcher(source, type_, mailing_name, workgroups):
    """Select importer and import contacts"""
    if type_ == 'vcard':
        return vcard_contacts_import(source, mailing_name, workgroups)
    elif type_ == 'text':
        return text_contacts_import(source, mailing_name, workgroups)
    elif type_ == 'excel':
        return excel_contacts_import(source, mailing_name, workgroups)
    return 0
