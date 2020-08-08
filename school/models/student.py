# See LICENSE file for full copyright and licensing details.

import time
import base64
from datetime import date
from odoo import models, fields, api, tools, _
from odoo.modules import get_module_resource
from odoo.exceptions import except_orm
from odoo.exceptions import ValidationError
from .import school

# from lxml import etree
# added import statement in try-except because when server runs on
# windows operating system issue arise because this library is not in Windows.
try:
    from odoo.tools import image_colorize, image_resize_image_big
except:
    image_colorize = False
    image_resize_image_big = False


class StudentStudent(models.Model):
    ''' Defining a student information '''
    _name = 'student.student'
    _table = "student_student"
    _description = 'Informasi Siswa'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False,
                access_rights_uid=None):
        '''Method to get student of parent having group teacher'''
        teacher_group = self.env.user.has_group('school.group_school_teacher')
        parent_grp = self.env.user.has_group('school.group_school_parent')
        login_user = self.env['res.users'].browse(self._uid)
        name = self._context.get('student_id')
        if name and teacher_group and parent_grp:
            parent_login_stud = self.env['school.parent'
                                         ].search([('partner_id', '=',
                                                  login_user.partner_id.id)
                                                   ])
            childrens = parent_login_stud.student_id
            args.append(('id', 'in', childrens.ids))
        return super(StudentStudent, self)._search(
            args=args, offset=offset, limit=limit, order=order, count=count,
            access_rights_uid=access_rights_uid)

    @api.depends('date_of_birth')
    def _compute_student_age(self):
        '''Method to calculate student age'''
        current_dt = date.today()
        for rec in self:
            if rec.date_of_birth:
                start = rec.date_of_birth
                age_calc = ((current_dt - start).days / 365)
                # Age should be greater than 0
                if age_calc > 0.0:
                    rec.age = age_calc

    @api.constrains('date_of_birth')
    def check_age(self):
        '''Method to check age should be greater than 5'''
        current_dt = date.today()
        if self.date_of_birth:
            start = self.date_of_birth
            age_calc = ((current_dt - start).days / 365)
            # Check if age less than 2 years
            if age_calc < 2:
                raise ValidationError(_('''Umur siswa harus lebih dari
                2 tahun!'''))

    @api.model
    def create(self, vals):
        '''Method to create user when student is created'''
        if vals.get('pid', _('New')) == _('New'):
            vals['pid'] = self.env['ir.sequence'
                                   ].next_by_code('student.student'
                                                  ) or _('New')
        if vals.get('pid', False):
            vals['login'] = vals['pid']
            vals['password'] = vals['pid']
        else:
            raise except_orm(_('Kesalahan!'),
                             _('''PID tidak valid
                                 baris tidak akan tersimpan.'''))
        if vals.get('company_id', False):
            company_vals = {'company_ids': [(4, vals.get('company_id'))]}
            vals.update(company_vals)
        if vals.get('email'):
            school.emailvalidation(vals.get('email'))
        res = super(StudentStudent, self).create(vals)
        teacher = self.env['school.teacher']
        for data in res.parent_id:
            teacher_rec = teacher.search([('stu_parent_id',
                                           '=', data.id)])
            for record in teacher_rec:
                record.write({'student_id': [(4, res.id, None)]})
        # Assign group to student based on condition
        emp_grp = self.env.ref('base.group_user')
        if res.state == 'draft':
            admission_group = self.env.ref('school.group_is_admission')
            new_grp_list = [admission_group.id, emp_grp.id]
            res.user_id.write({'groups_id': [(6, 0, new_grp_list)]})
        elif res.state == 'done':
            done_student = self.env.ref('school.group_school_student')
            group_list = [done_student.id, emp_grp.id]
            res.user_id.write({'groups_id': [(6, 0, group_list)]})
        return res

    
    def write(self, vals):
        teacher = self.env['school.teacher']
        if vals.get('parent_id'):
            for parent in vals.get('parent_id')[0][2]:
                teacher_rec = teacher.search([('stu_parent_id',
                                               '=', parent)])
                for data in teacher_rec:
                    data.write({'student_id': [(4, self.id)]})
        return super(StudentStudent, self).write(vals)

    @api.model
    def _default_image(self):
        '''Method to get default Image'''
        image_path = get_module_resource('hr', 'static/src/img',
                                         'default_image.png')
        return tools.image_resize_image_big(base64.b64encode(open(image_path,
                                                                  'rb').read()
                                                             ))

    @api.depends('state')
    def _compute_teacher_user(self):
        for rec in self:
            if rec.state == 'done':
                teacher = self.env.user.has_group("school.group_school_teacher"
                                                  )
                if teacher:
                    rec.teachr_user_grp = True

    @api.model
    def check_current_year(self):
        '''Method to get default value of logged in Student'''
        res = self.env['academic.year'].search([('current', '=',
                                                 True)])
        if not res:
            raise ValidationError(_('''Tidak ada tahun ajaran saat ini yang didefinisikan!
                                    Mohon hubungi Admin!'''
                                    ))
        return res.id

    family_con_ids = fields.One2many('student.family.contact',
                                     'family_contact_id',
                                     'Detil kontak keluarga',
                                     states={'done': [('readonly', True)]})
    user_id = fields.Many2one('res.users', 'ID User', ondelete="cascade",
                              required=True, delegate=True)
    student_name = fields.Char('Nama Siswa', related='user_id.name',
                               store=True, readonly=True)
    pid = fields.Char('Nomor Induk', required=True,
                      default=lambda self: _('New'),
                      help='Nomor Induk Siswa')
    reg_code = fields.Char('Nomor Pendaftaran',
                           help='Nomor kode pendaftaran siswa')
    student_code = fields.Char('Kode Siswa')
    contact_phone = fields.Char('Telp.')
    contact_mobile = fields.Char('Handphone.')
    roll_no = fields.Integer('Nomor Urut.', readonly=True)
    photo = fields.Binary('Foto', default=_default_image)
    year = fields.Many2one('academic.year', 'Tahun Ajaran', readonly=True,
                           default=check_current_year)
    cast_id = fields.Many2one('student.cast', 'Agama')
    relation = fields.Many2one('student.relation.master', 'Hubungan')

    admission_date = fields.Date('Tanggal Masuk', default=date.today())
    middle = fields.Char('Nama Tengah', required=True,
                         states={'done': [('readonly', True)]})
    last = fields.Char('Nama Belakang', required=True,
                       states={'done': [('readonly', True)]})
    gender = fields.Selection([('male', 'Laki-Laki'), ('female', 'Perempuan')],
                              'Jenis Kelamin', states={'done': [('readonly', True)]})
    date_of_birth = fields.Date('Tanggal Lahir', required=True,
                                states={'done': [('readonly', True)]})
    mother_tongue = fields.Many2one('mother.toungue', "Bahasa Ibu")
    age = fields.Integer(compute='_compute_student_age', string='Umur',
                         readonly=True)
    reference_ids = fields.One2many('student.reference', 'reference_id',
                                    'Referensi',
                                    states={'done': [('readonly', True)]})
    previous_school_ids = fields.One2many('student.previous.school',
                                          'previous_school_id',
                                          'Detil Sekolah Sebelumnya',
                                          states={'done': [('readonly',
                                                            True)]})
    doctor = fields.Char('Nama Dokter', states={'done': [('readonly', True)]})
    designation = fields.Char('Gelar')
    doctor_phone = fields.Char('Telp Dokter.')
    blood_group = fields.Char('Golongan Darah')
    height = fields.Float('Tinggi', help="Tinggi dalam sentimeter")
    weight = fields.Float('Berat', help="Berat dalam kilogram")
    eye = fields.Boolean('Mata')
    ear = fields.Boolean('Telinga')
    nose_throat = fields.Boolean('Hidung & Tenggorokan')
    respiratory = fields.Boolean('Pernafasan')
    cardiovascular = fields.Boolean('Jantung')
    neurological = fields.Boolean('Saraf')
    muskoskeletal = fields.Boolean('Ortopedi')
    dermatological = fields.Boolean('Kulit')
    blood_pressure = fields.Boolean('Tekanan Darah')
    remark = fields.Text('Catatan', states={'done': [('readonly', True)]})
    school_id = fields.Many2one('school.school', 'Jenjang',
                                states={'done': [('readonly', True)]})
    state = fields.Selection([('draft', 'Draft'),
                              ('done', 'Selesai'),
                              ('terminate', 'Dikeluarkan'),
                              ('cancel', 'Dibatalkan'),
                              ('alumni', 'Alumni')],
                             'Status', readonly=True, default="draft")
    history_ids = fields.One2many('student.history', 'student_id', 'Rekam Siswa')
    certificate_ids = fields.One2many('student.certificate', 'student_id',
                                      'Sertifikat')
    student_discipline_line = fields.One2many('student.descipline',
                                              'student_id', 'Tindakan Disiplin')
    document = fields.One2many('student.document', 'doc_id', 'Dokumen')
    description = fields.One2many('student.description', 'des_id',
                                  'Keterangan')
    award_list = fields.One2many('student.award', 'award_list_id',
                                 'Penghargaan')
    stu_name = fields.Char('Nama Depan', related='user_id.name',
                           readonly=True)
    Acadamic_year = fields.Char('Tahun Ajaran', related='year.name',
                                help='Tahun Ajaran', readonly=True)
    division_id = fields.Many2one('standard.division', 'Kelas')
    standard_id = fields.Many2one('school.standard', 'Tingkat')
    parent_id = fields.Many2many('school.parent', 'students_parents_rel',
                                 'student_id',
                                 'students_parent_id', 'Orang Tua',
                                 states={'done': [('readonly', True)]})
    terminate_reason = fields.Text('Alasan Dikeluarkan')
    active = fields.Boolean(default=True)
    teachr_user_grp = fields.Boolean("Kelompok Guru",
                                     compute="_compute_teacher_user",
                                     )
    active = fields.Boolean(default=True)

    
    def set_to_draft(self):
        '''Method to change state to draft'''
        self.state = 'draft'

    
    def set_alumni(self):
        '''Method to change state to alumni'''
        student_user = self.env['res.users']
        for rec in self:
            rec.state = 'alumni'
            rec.standard_id._compute_total_student()
            user = student_user.search([('id', '=',
                                         rec.user_id.id)])
            rec.active = False
            if user:
                user.active = False

    
    def set_done(self):
        '''Method to change state to done'''
        self.state = 'done'

    
    def admission_draft(self):
        '''Set the state to draft'''
        self.state = 'draft'

    
    def set_terminate(self):
        self.state = 'terminate'

    
    def cancel_admission(self):
        self.state = 'cancel'

    
    def admission_done(self):
        '''Method to confirm admission'''
        school_standard_obj = self.env['school.standard']
        ir_sequence = self.env['ir.sequence']
        student_group = self.env.ref('school.group_school_student')
        emp_group = self.env.ref('base.group_user')
        for rec in self:
            if not rec.standard_id:
                raise ValidationError(_('''Mohon pilih tingkat kelas!'''))
            if rec.standard_id.remaining_seats <= 0:
                raise ValidationError(_('Seats of class %s are full'
                                        ) % rec.standard_id.standard_id.name)
            domain = [('school_id', '=', rec.school_id.id)]
            # Checks the standard if not defined raise error
            if not school_standard_obj.search(domain):
                raise except_orm(_('Warning'),
                                 _('''Tingkat kelas belum dibuat di
                                     jenjang sekolah'''))
            # Assign group to student
            rec.user_id.write({'groups_id': [(6, 0, [emp_group.id,
                                                     student_group.id])]})
            # Assign roll no to student
            number = 1
            for rec_std in rec.search(domain):
                rec_std.roll_no = number
                number += 1
            # Assign registration code to student
            reg_code = ir_sequence.next_by_code('student.registration')
            registation_code = (str(rec.school_id.state_id.name) + str('/') +
                                str(rec.school_id.city) + str('/') +
                                str(rec.school_id.name) + str('/') +
                                str(reg_code))
            stu_code = ir_sequence.next_by_code('student.code')
            student_code = (str(rec.school_id.code) + str('/') +
                            str(rec.year.code) + str('/') +
                            str(stu_code))
            rec.write({'state': 'done',
                       'admission_date': time.strftime('%Y-%m-%d'),
                       'student_code': student_code,
                       'reg_code': registation_code})
        return True
