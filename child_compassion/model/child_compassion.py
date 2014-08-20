# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Cyril Sester. Copyright Compassion Suisse
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import requests
import json
import logging
logger = logging.getLogger(__name__)
from openerp.osv import orm, fields
from openerp.tools.translate import _


class compassion_child(orm.Model):
    """ A sponsored child """
    _name = 'compassion.child'
    _columns = {
        'name': fields.char(_("Name"),size=128,required=True),
        'code': fields.char(_("Child code"),size=128,required=True),
        'unique_id': fields.char(_("Unique ID"),size=128),
        'birthdate': fields.date(_("Birthdate")),
        'type': fields.selection(
            [('CDSP', 'CDSP'),
             ('LDP', 'LDP')], _('Type of sponsorship program'), required=True),
        'date': fields.date(_("Allocation date"),
                            help=_("The date at which Compass allocated this child to Switzerland")),
        'gender': fields.selection(
            [('F', _('Female')),
            ('M', _('Male'))], _('Gender')),
        'completion_date': fields.date(_("Completion date")),
        'desc_en': fields.text(_('English description')),
        'desc_fr': fields.text(_('French description')),
        'desc_de': fields.text(_('German description')),
        'desc_it': fields.text(_('Italian description')),
        'start_date': fields.date(_("Start date")),
        'case_study_ids': fields.one2many(
            'compassion.child.property', 'child_id', string=_('Case studies'),
            readonly=False), #FIXME readonly
        'portrait': fields.binary(_('Portrait')),
    }
    
    _defaults = {
        'type' : 'CDSP'
    }
    
    def get_last_case_study(self, cr, uid, child_id, context=None):
        ''' Get the most recent case study and updates portrait picture '''
        child = self.browse(cr, uid, child_id, context)[0]
        return self._get_case_study(cr, uid, child, context)

    def generate_descriptions(self, cr, uid, child_id, context=None):
        child = self.browse(cr, uid, child_id, context)
        if not child:
            raise orm.except_orm('ObjectError', _('No valid child id given !'))
        child = child[0]
        if not child.case_study_ids:
            raise orm.except_orm('ValueError', _('Cannot generate a description for a child '
                                                 'without a case study'))
        case_study = child.case_study_ids[-1]
        desc_fr = self.gen_fr_translation(cr, uid, child, case_study, context)
        self.write(cr, uid, child_id, {'desc_fr': desc_fr})

    def gen_fr_translation(self, cr, uid, child, case_study, context=None):
        desc_fr = self._gen_christ_act_fr(cr, uid, child, case_study, context)
        desc_fr += self._gen_family_act_info(cr, uid, child, case_study, context)
        desc_fr += self._gen_hobbies_info(cr, uid, child, case_study, context)
        desc_fr += self._get_school_info(cr, uid, child, case_study, context)
        return desc_fr
        
    def _gen_christ_act_fr(self, cr, uid, child, case_study, context=None):
        if not case_study.christian_activities_ids:
            return ''
        activities = [activity.value_fr_m if activity.value_fr_m else activity.value_en 
                      for activity in case_study.christian_activities_ids]
        activities_str = ', '.join(activities[:-1])
        if len(activities) > 1:
            activities_str += ' et '
        activities_str += activities[-1]
        string = u"A l'Église, %s participe %s." % (child.name, activities_str)
        return string

    def _gen_family_act_info(self, cr, uid, child, case_study, context=None):
        if not case_study.family_duties_ids:
            return ''
        speciales = ['carries water', 'animal care', 'running errands', 'buying/selling in market'
                     'gathers firewood', 'teaching others']
        activities = [activity.value_fr_m if activity.value_fr_m else activity.value_en
                      for activity in case_study.family_duties_ids
                      if activity.value_en not in speciales]
        if len(activities):
            activities[0] = u'aide à faire %s' % activities[0]
        activities.extend([activity.value_fr_m if activity.value_fr_m else activity.value_en
                           for activity in case_study.family_duties_ids
                           if activity.value_en in speciales])
        activities_str = ', '.join(activities[:-1])
        if len(activities) > 1:
            activities_str += ' et '
        activities_str += activities[-1]
        string = u"A la maison, %s %s. " % (child.name, activities_str)
        return string

    def _gen_hobbies_info(self, cr, uid, child, case_study, context=None):
        if not case_study.hobbies_ids:
            return ''
        verbs = ['art/drawing', 'bicycling', 'jump rope', 'listening to music'
                 'musical instrument', 'reading', 'running', 'singing', 'story telling',
                 'swimming', 'walking']
        activities = [activity.value_fr_m if activity.value_fr_m else activity.value_en
                      for activity in case_study.hobbies_ids
                      if activity.value_en not in verbs]
        if len(activities):
            activities[0] = u'jouer %s' % activities[0]
        activities.extend([activity.value_fr_m if activity.value_fr_m else activity.value_en
                           for activity in case_study.hobbies_ids
                           if activity.value_en in verbs])
        activities_str = ', '.join(activities[:-1])
        if len(activities) > 1:
            activities_str += ' et '
        activities_str += activities[-1]
        string = u"%s aime beaucoup %s. " % ('Il' if child.gender == 'M' else 'Elle', activities_str)
        return string

    def _get_school_info(self, cr, uid, child, case_study, context=None):
        ordinals = [u'première', u'deuxième', u'troisième', u'quatrième', u'cinquième',
                    u'sixième', u'septième', u'huitième', u'neuvième', u'dixième', u'onzième',
                    u'douzième', u'treizième', u'quatorzième', u'quinzième']
        string = u'Il' if child.gender == 'M' else u'Elle'
        if case_study.attending_school_flag:
            if case_study.us_school_level and int(case_study.us_school_level) < 16:
                string += u' est en %s année' % ordinals[int(case_study.us_school_level)-1]
            else:
                string += u' va à l\'école'
            if case_study.school_performance:
                string += u' et %s a des résultats %s. ' % (child.name, 
                          case_study.school_performance[0].value_fr_m
                          if case_study.school_performance[0].value_fr_m
                            else case_study.school_performance[0].value_en)
            elif case_study.school_best_subject:
                string += ' et aime bien %s. ' % (case_study.school_best_subject[0].value_fr_m
                          if case_study.school_best_subject[0].value_fr_m
                            else case_study.school_best_subject[0].value_en)
            else:
                string += '.'
        else:
            string += ' ne va pas à l\'école. ' #TODO reason

        return string

    def _get_case_study(self, cr, uid, child, context=None):
        ''' Returns id of generated case_study or None if failed '''
        r = requests.get('https://api2.compassion.com/iptest/ci/v1/child/' + child.code + '/casestudy?api_key=jykapanuupqsrgc7se4q4v2c')
        if not r.status_code/100 == 2:
            logger.info("Return code : %s" % r.status_code)
            return None
        
        case_study = json.loads(r.text)
        vals = {}
        vals['child_id'] = child.id
        vals['info_date'] = case_study['ChildCaseStudyDate']
        values = []
        if case_study['ChristianActivities'].get('ChristianActivity'):
            values.extend(self._get_values(
                cr, uid, case_study['ChristianActivities']['ChristianActivity'],
                'christian_activities', context))
        if not case_study['OtherChristianActivities'] == 'None':
            values.append(self._get_value_id(cr, uid, 
                                        case_study['OtherChristianActivities'], 'christian_activities'))
        if case_study['FamilyDuties'].get('FamilyDuty'):
            values.extend(self._get_values(
                cr, uid, case_study['FamilyDuties']['FamilyDuty'],
                'family_duties', context))
        if not case_study['OtherFamilyDuties'] == 'None':
            values.append(self._get_value_id(cr, uid, 
                                        case_study['OtherFamilyDuties'], 'family_duties'))
        if case_study['HobbiesAndSports'].get('Hobby'):
            values.extend(self._get_values(
                cr, uid, case_study['HobbiesAndSports']['Hobby'],
                'hobbies', context))
        if not case_study['OtherHobbies'] == 'None':
            values.append(self._get_value_id(cr, uid, 
                                        case_study['OtherHobbies'], 'hobbies'))
        if type(case_study['HealthConditions']) is dict and \
                case_study['HealthConditions'].get('HealthCondition'):
            values.extend(self._get_values(
                cr, uid, case_study['HealthConditions']['HealthCondition'],
                'health_conditions', context))
        if not case_study['OtherHealthConditions'] == 'None':
            values.append(self._get_value_id(cr, uid, 
                                        case_study['OtherHealthConditions'], 'health_conditions'))
        if case_study['Guardians'].get('Guardian'):
            values.extend(self._get_values(
                cr, uid, case_study['Guardians']['Guardian'],
                'guardians', context))
        for key, value in case_study['NaturalParents'].iteritems():
            property_name = ''
            if key.startswith('Father'):
                property_name = 'father'
            elif key.startswith('Mother'):
                property_name = 'mother'
            else:
                continue

            if value == 'false' or value == '':
                continue
            elif value == 'true':
                value = key.replace('Father', '').replace('Mother', '')
            values.append(self._get_value_id(cr, uid, value, property_name, context))
        values.append(self._get_value_id(cr, uid, case_study['NaturalParents']['MaritalStatusOfParents'], 
                                         'marital_status', context))
        for key, value in case_study['Employment'].iteritems():
            property_name = ''
            if key.startswith('Father'):
                property_name = 'male_guardian'
            elif key.startswith('Mother'):
                property_name = 'female_guardian'
            else:
                continue

            if value == 'false' or value == '':
                continue
            elif value == 'true':
                value = key.replace('FatherOrMaleGuardian', '').replace('MotherOrFemaleGuardian', '')
            values.append(self._get_value_id(cr, uid, value, property_name, context))
        vals['us_school_level'] = case_study['Schooling']['USSchoolEquivalent']
        values.append(self._get_value_id(cr, uid, case_study['Schooling']['SchoolPerformance'], 
                                         'school_performance', context))
        values.append(self._get_value_id(cr, uid, case_study['Schooling']['ChildsBestSubject'], 
                                         'school_best_subject', context))
        vals['attending_school_flag'] = bool(case_study['Schooling']['ChildAttendingSchool'])
        vals['family_size'] = int(case_study['FamilySize']['TotalFamilyFemalesUnder18'])
        vals['family_size'] += int(case_study['FamilySize']['TotalFamilyMalesUnder18'])
        vals['hobbies_ids'] = [(6, 0, values)]
        child_prop_obj = self.pool.get('compassion.child.property')
        prop_id = child_prop_obj.create(cr, uid, vals, context)
        return prop_id

    def _get_picture(self, cr, uid, child_code, context=None):
        ''' Gets a picture from Compassion webservice.
            @param TODO
        '''
        return False

    def _get_values(self, cr, uid, _list, property_name, context):
        value_ids = []
        for elem in _list:
            value_ids.append(self._get_value_id(cr, uid, elem,
                                                          property_name, context))
        return value_ids

    def _get_value_id(self, cr, uid, value, property_name, context=None):
        prop_val_obj = self.pool.get('compassion.child.property.value')
        value = value.lower()
        val_ids = prop_val_obj.search(cr, uid, [('value_en', '=like', value),
                                                ('property_name', '=', property_name)], context=context)
        if val_ids:
            return val_ids[0]
        prop_id = prop_val_obj.create(cr, uid, {'property_name': property_name,
                                                'value_en': value})
        return prop_id