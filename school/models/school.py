# See LICENSE file for full copyright and licensing details.

# import time
import re
import calendar
from datetime import datetime, date
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import except_orm
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


EM = (r"[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$")


def emailvalidation(email):

    if email:
        EMAIL_REGEX = re.compile(EM)
        if not EMAIL_REGEX.match(email):
            raise ValidationError(_('''Format email tidak dikenal atau salah.
            Mohon masukan email yang benar!'''))
        else:
            return True


class AcademicYear(models.Model):
    ''' Defines an academic year '''
    _name = "academic.year"
    _description = "Tahun Pelajaran"
    _order = "sequence"

    sequence = fields.Integer('Sequence', required=True,
                              help="Urutan sequence yang ingin anda lihat tahun ini.")
    name = fields.Char('Tahun Ajaran', required=True, help='Nama tahun ajaran')
    code = fields.Char('Kode', required=True, help='Kode tahun ajaran')
    date_start = fields.Date('Tanggal Mulai', required=True,
                             help='Tanggal tahun ajaran baru')
    date_stop = fields.Date('Tanggal Akhir', required=True,
                            help='Akhir tahun ajaran')
    month_ids = fields.One2many('academic.month', 'year_id', 'Bulan',
                                help="Bulan dalam tahun ajaran")
    grade_id = fields.Many2one('grade.master', "Nilai")
    current = fields.Boolean('Sekarang', help="Set tahun ajaran aktif")
    description = fields.Text('Keterangan')

    @api.model
    def next_year(self, sequence):
        '''This method assign sequence to years'''
        year_id = self.search([('sequence', '>', sequence)], order='id',
                              limit=1)
        if year_id:
            return year_id.id
        return False

    @api.multi
    def name_get(self):
        '''Method to display name and code'''
        return [(rec.id, ' [' + rec.code + ']' + rec.name) for rec in self]

    @api.multi
    def generate_academicmonth(self):
        interval = 1
        month_obj = self.env['academic.month']
        for data in self:
            ds = data.date_start
            while ds < data.date_stop:
                de = ds + relativedelta(months=interval, days=-1)
                if de > data.date_stop:
                    de = data.date_stop
                month_obj.create({
                    'name': ds.strftime('%B'),
                    'code': ds.strftime('%m/%Y'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'year_id': data.id,
                })
                ds = ds + relativedelta(months=interval)
        return True

    @api.constrains('date_start', 'date_stop')
    def _check_academic_year(self):
        '''Method to check start date should be greater than end date
           also check that dates are not overlapped with existing academic
           year'''
        new_start_date = self.date_start
        new_stop_date = self.date_stop
        delta = new_stop_date - new_start_date
        if delta.days > 365 and not calendar.isleap(new_start_date.year):
            raise ValidationError(_('''Kesalahan! Durasi tahun ajaran
                                      salah.'''))
        if (self.date_stop and self.date_start and
                self.date_stop < self.date_start):
            raise ValidationError(_('''Tanggal mulai tahun ajaran baru'
                                      harus lebih kecil dari tanggal berakhir.'''))
        for old_ac in self.search([('id', 'not in', self.ids)]):
            # Check start date should be less than stop date
            if (old_ac.date_start <= self.date_start <= old_ac.date_stop or
                    old_ac.date_start <= self.date_stop <= old_ac.date_stop):
                raise ValidationError(_('''Kesalahan! Anda tidak dapat membuat kalender
                                          yang overlap.'''))

    @api.constrains('current')
    def check_current_year(self):
        check_year = self.search([('current', '=', True)])
        if len(check_year.ids) >= 2:
            raise ValidationError(_('''Kesalahan! Anda tidak dapat membuat dua tahun
            ajaran yang aktif!'''))


class AcademicMonth(models.Model):
    ''' Defining a month of an academic year '''
    _name = "academic.month"
    _description = "Academic Month"
    _order = "date_start"

    name = fields.Char('Nama', required=True, help='Nama bulan dalam tahun ajaran')
    code = fields.Char('Kode', required=True, help='Kode bulan dalam tahun ajaran')
    date_start = fields.Date('Mulai Periode', required=True,
                             help='Awal periode bulan')
    date_stop = fields.Date('Akhir Periode', required=True,
                            help='Akhir periode bulan')
    year_id = fields.Many2one('academic.year', 'Tahun Ajaran', required=True,
                              help="Tahun ajaran terkait ")
    description = fields.Text('Keterangan')

    _sql_constraints = [
        ('month_unique', 'unique(date_start, date_stop, year_id)',
         'Bulan dalam tahun ajaran tidak boleh sama!'),
    ]

    @api.constrains('date_start', 'date_stop')
    def _check_duration(self):
        '''Method to check duration of date'''
        if (self.date_stop and self.date_start and
                self.date_stop < self.date_start):
            raise ValidationError(_(''' Akhir periode harus lebih besar
                                    daripada awal periode!'''))

    @api.constrains('year_id', 'date_start', 'date_stop')
    def _check_year_limit(self):
        '''Method to check year limit'''
        if self.year_id and self.date_start and self.date_stop:
            if (self.year_id.date_stop < self.date_stop or
                    self.year_id.date_stop < self.date_start or
                    self.year_id.date_start > self.date_start or
                    self.year_id.date_start > self.date_stop):
                raise ValidationError(_('''Bulan salah ! Sebagian bulan overlap
                                    atau tanggal pada periode tidak termasuk
                                    didalam tahun ajaran!'''))

    @api.constrains('date_start', 'date_stop')
    def check_months(self):
        for old_month in self.search([('id', 'not in', self.ids)]):
            # Check start date should be less than stop date
            if old_month.date_start <= \
                    self.date_start <= old_month.date_stop \
                    or old_month.date_start <= \
                    self.date_stop <= old_month.date_stop:
                    raise ValidationError(_('''Kesalahan! Anda tidak dapat membuat
                    bulan yang overlap!'''))


class StandardDivision(models.Model):
    ''' Defining a division(A, B, C) related to standard'''
    _name = "standard.division"
    _description = "Nama Kelas"
    _order = "sequence"

    sequence = fields.Integer('Sequence', required=True)
    name = fields.Char('Name Kelas', required=True)
    code = fields.Char('Kode', required=True)
    description = fields.Text('Keterangan')


class StandardStandard(models.Model):
    ''' Defining Standard Information '''
    _name = 'standard.standard'
    _description = 'Tingkat Kelas'
    _order = "sequence"

    sequence = fields.Integer('Sequence', required=True)
    name = fields.Char('Tingkat Kelas', required=True)
    code = fields.Char('Kode', required=True)
    description = fields.Text('Keterangan')

    @api.model
    def next_standard(self, sequence):
        '''This method check sequence of standard'''
        stand_ids = self.search([('sequence', '>', sequence)], order='id',
                                limit=1)
        if stand_ids:
            return stand_ids.id
        return False


class SchoolStandard(models.Model):
    ''' Defining a standard related to school '''
    _name = 'school.standard'
    _description = 'Kelas Sekolah'
    _rec_name = "standard_id"

    @api.depends('standard_id', 'school_id', 'division_id')
    def _compute_student(self):
        '''Compute student of done state'''
        student_obj = self.env['student.student']
        for rec in self:
            rec.student_ids = student_obj.\
                search([('standard_id', '=', rec.id),
                        ('school_id', '=', rec.school_id.id),
                        ('division_id', '=', rec.division_id.id),
                        ('state', '=', 'done')])

    @api.onchange('standard_id', 'division_id')
    def onchange_combine(self):
        self.name = str(self.standard_id.name
                        ) + '-' + str(self.division_id.name)

    @api.depends('subject_ids')
    def _compute_subject(self):
        '''Method to compute subjects'''
        for rec in self:
            rec.total_no_subjects = len(rec.subject_ids)

    @api.depends('student_ids')
    def _compute_total_student(self):
        for rec in self:
            rec.total_students = len(rec.student_ids)

    @api.depends("capacity", "total_students")
    def _compute_remain_seats(self):
        for rec in self:
            rec.remaining_seats = rec.capacity - rec.total_students

    school_id = fields.Many2one('school.school', 'Sekolah', required=True)
    standard_id = fields.Many2one('standard.standard', 'Tingkat',
                                  required=True)
    division_id = fields.Many2one('standard.division', 'Nama Kelas',
                                  required=True)
    subject_ids = fields.Many2many('subject.subject', 'subject_standards_rel',
                                   'subject_id', 'standard_id', 'Mata Pelajaran')
    user_id = fields.Many2one('school.teacher', 'Guru Kelas')
    student_ids = fields.One2many('student.student', 'standard_id',
                                  'Murid Terdaftar',
                                  compute='_compute_student', store=True
                                  )
    color = fields.Integer('Color Index')
    cmp_id = fields.Many2one('res.company', 'Nama Sekolah/Yayasan',
                             related='school_id.company_id', store=True)
    syllabus_ids = fields.One2many('subject.syllabus', 'standard_id',
                                   'Silabus Pelajaran')
    total_no_subjects = fields.Integer('Jumlah Mata Pelajaran',
                                       compute="_compute_subject")
    name = fields.Char('Nama Tingkat')
    capacity = fields.Integer("Jumlah Kursi")
    total_students = fields.Integer("Jumlah Siswa",
                                    compute="_compute_total_student",
                                    store=True)
    remaining_seats = fields.Integer("Kursi Tersisa",
                                     compute="_compute_remain_seats",
                                     store=True)
    class_room_id = fields.Many2one('class.room', 'Ruang Kelas')

    @api.constrains('standard_id', 'division_id')
    def check_standard_unique(self):
        standard_search = self.env['school.standard'
                                   ].search([('standard_id', '=',
                                              self.standard_id.id),
                                             ('division_id', '=',
                                              self.division_id.id),
                                             ('school_id', '=',
                                              self.school_id.id),
                                             ('id', 'not in', self.ids)])
        if standard_search:
            raise ValidationError(_('''Tingkat dan nama kelas tidak boleh sama!'''
                                    ))

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.student_ids or rec.subject_ids or rec.syllabus_ids:
                raise ValidationError(_('''Anda tidak bisa menghapus tingkatan ini
                karena ada siswa, atau mata pejaran atau
                syllabus yang terdaftar!'''))
        return super(SchoolStandard, self).unlink()

    @api.constrains('capacity')
    def check_seats(self):
        if self.capacity <= 0:
            raise ValidationError(_('''Kapasitas kursi harus lebih besar dari
                0!'''))

    @api.multi
    def name_get(self):
        '''Method to display standard and division'''
        return [(rec.id, rec.standard_id.name + '[' + rec.division_id.name +
                 ']') for rec in self]


class SchoolSchool(models.Model):
    ''' Defining School Information '''
    _name = 'school.school'
    _description = 'Informasi sekolah'
    _rec_name = "com_name"

    @api.model
    def _lang_get(self):
        '''Method to get language'''
        languages = self.env['res.lang'].search([])
        return [(language.code, language.name) for language in languages]

    company_id = fields.Many2one('res.company', 'Sekolah/Yayasan',
                                 ondelete="cascade",
                                 required=True,
                                 delegate=True)
    com_name = fields.Char('Nama Sekolah', related='company_id.name',
                           store=True)
    code = fields.Char('Kode', required=True)
    standards = fields.One2many('school.standard', 'school_id',
                                'Tingkat')
    lang = fields.Selection(_lang_get, 'Bahasa',
                            help='''Jika bahasa diset disini maka
                            seluruh data partner akan menggunakan
                            bahasa ini, jika tidak maka akan mengunakan
                            bahasa inggris''')

    @api.model
    def create(self, vals):
        res = super(SchoolSchool, self).create(vals)
        main_company = self.env.ref('base.main_company')
        res.company_id.parent_id = main_company.id
        return res


class SubjectSubject(models.Model):
    '''Defining a subject '''
    _name = "subject.subject"
    _description = "Mata Pelajaran"

    name = fields.Char('Name', required=True)
    code = fields.Char('Kode', required=True)
    maximum_marks = fields.Integer("Nilai Maksimal")
    minimum_marks = fields.Integer("Nilai Minimal")
    weightage = fields.Integer("Bobot")
    teacher_ids = fields.Many2many('school.teacher', 'subject_teacher_rel',
                                   'subject_id', 'teacher_id', 'Guru')
    standard_ids = fields.Many2many('standard.standard',
                                    string='Tingkat')
    standard_id = fields.Many2one('standard.standard', 'Kelas')
    is_practical = fields.Boolean('Kelas Praktek?',
                                  help='Cek disini jika kelas praktek.')
    elective_id = fields.Many2one('subject.elective')
    student_ids = fields.Many2many('student.student',
                                   'elective_subject_student_rel',
                                   'subject_id', 'student_id', 'Siswa')


class SubjectSyllabus(models.Model):
    '''Defining a  syllabus'''
    _name = "subject.syllabus"
    _description = "Silabus"
    _rec_name = "subject_id"

    standard_id = fields.Many2one('school.standard', 'Tingkat')
    subject_id = fields.Many2one('subject.subject', 'Mata Pelajaran')
    syllabus_doc = fields.Binary("Dokumen Silabus",
                                 help="Attach silabus mata pelajaran")


class SubjectElective(models.Model):
    ''' Defining Subject Elective '''
    _name = 'subject.elective'
    _description = "Pilihan mata pelajaran"

    name = fields.Char("Name")
    subject_ids = fields.One2many('subject.subject', 'elective_id',
                                  'Pilihan Mata Pelajaran')


class MotherTongue(models.Model):
    _name = 'mother.toungue'
    _description = "Bahasa Ibu"

    name = fields.Char("Bahasa Ibu")


class StudentAward(models.Model):
    _name = 'student.award'
    _description = "Prestasi Siswa"

    award_list_id = fields.Many2one('student.student', 'Student')
    name = fields.Char('Nama Prestasi')
    description = fields.Char('Keterangan')


class AttendanceType(models.Model):
    _name = "attendance.type"
    _description = "Tipe Absen"

    name = fields.Char('Nama', required=True)
    code = fields.Char('Kode', required=True)


class StudentDocument(models.Model):
    _name = 'student.document'
    _description = "Dokumen Siswa"
    _rec_name = "doc_type"

    doc_id = fields.Many2one('student.student', 'Siswa')
    file_no = fields.Char('Nomor Dokumen', readonly="1", default=lambda obj:
                          obj.env['ir.sequence'].
                          next_by_code('student.document'))
    submited_date = fields.Date('Diajukan tanggal')
    doc_type = fields.Many2one('document.type', 'Tipe Dokumen', required=True)
    file_name = fields.Char('Nama Dokumen',)
    return_date = fields.Date('Dikembalikan tanggal')
    new_datas = fields.Binary('Attachments')


class DocumentType(models.Model):
    ''' Defining a Document Type(SSC,Leaving)'''
    _name = "document.type"
    _description = "Tipe Dokumen"
    _rec_name = "doc_type"
    _order = "seq_no"

    seq_no = fields.Char('Sequence', readonly=True,
                         default=lambda self: _('New'))
    doc_type = fields.Char('Tipe Dokumen', required=True)

    @api.model
    def create(self, vals):
        if vals.get('seq_no', _('New')) == _('New'):
            vals['seq_no'] = self.env['ir.sequence'
                                      ].next_by_code('document.type'
                                                     ) or _('New')
        return super(DocumentType, self).create(vals)


class StudentDescription(models.Model):
    ''' Defining a Student Description'''
    _name = 'student.description'
    _description = "Keterangan Siswa"

    des_id = fields.Many2one('student.student', 'Referensi Siswa')
    name = fields.Char('Nama')
    description = fields.Char('Keterangan')


class StudentDescipline(models.Model):
    _name = 'student.descipline'
    _description = "Tindakan Disiplin"

    student_id = fields.Many2one('student.student', 'Siswa')
    teacher_id = fields.Many2one('school.teacher', 'Guru')
    date = fields.Date('Tanggal')
    class_id = fields.Many2one('standard.standard', 'Kelas')
    note = fields.Text('Catatan')
    action_taken = fields.Text('Tindakan yang dilakukan')


class StudentHistory(models.Model):
    _name = "student.history"
    _description = "Histori Siswa"

    student_id = fields.Many2one('student.student', 'Siswa')
    academice_year_id = fields.Many2one('academic.year', 'Tahun Pelajaran',
                                        )
    standard_id = fields.Many2one('school.standard', 'Tingkat')
    percentage = fields.Float("Persentasi", readonly=True)
    result = fields.Char('Hasil', readonly=True)


class StudentCertificate(models.Model):
    _name = "student.certificate"
    _description = "Sertifikat Siswa"

    student_id = fields.Many2one('student.student', 'Siswa')
    description = fields.Char('Keterangan')
    certi = fields.Binary('Sertifikat', required=True)


class StudentReference(models.Model):
    ''' Defining a student reference information '''
    _name = "student.reference"
    _description = "Referensi Siswa"

    reference_id = fields.Many2one('student.student', 'Siswa')
    name = fields.Char('Nama Depan', required=True)
    middle = fields.Char('Nama Tengah', required=True)
    last = fields.Char('Nama Belakang', required=True)
    designation = fields.Char('Gelar', required=True)
    phone = fields.Char('Telp', required=True)
    gender = fields.Selection([('male', 'Laki-Laki'), ('female', 'Perempuan')],
                              'Jenis Kelamin')


class StudentPreviousSchool(models.Model):
    ''' Defining a student previous school information '''
    _name = "student.previous.school"
    _description = "Sekolah Sebelumnya"

    previous_school_id = fields.Many2one('student.student', 'Siswa')
    name = fields.Char('Nama', required=True)
    registration_no = fields.Char('Nomor Pendaftara.', required=True)
    admission_date = fields.Date('Tanggal Diterima')
    exit_date = fields.Date('Tanggal Keluar')
    course_id = fields.Many2one('standard.standard', 'Tingkat', required=True)
    add_sub = fields.One2many('academic.subject', 'add_sub_id', 'Mata Pelajaran')

    @api.constrains('admission_date', 'exit_date')
    def check_date(self):
        curr_dt = date.today()
        if self.admission_date >= curr_dt or self.exit_date >= curr_dt:
            raise ValidationError(_('''Tanggal masuk dan keluar harus
            lebih kecil dari tanggal saat ini!'''))
        if self.admission_date > self.exit_date:
            raise ValidationError(_(''' Tanggal masuk harus lebih kecil
            daripada tanggal keluar di sekolah sebelumnya'''))


class AcademicSubject(models.Model):
    ''' Defining a student previous school information '''
    _name = "academic.subject"
    _description = "Pelajaran Sekolah Sebelumnya"

    add_sub_id = fields.Many2one('student.previous.school', 'Tambah Mata Pelajaran',
                                 invisible=True)
    name = fields.Char('Nama', required=True)
    maximum_marks = fields.Integer("Nilai Maksimal")
    minimum_marks = fields.Integer("Nilai Minimal")


class StudentFamilyContact(models.Model):
    ''' Defining a student emergency contact information '''
    _name = "student.family.contact"
    _description = "Kontak Keluarga Siswa"

    @api.depends('relation', 'stu_name')
    def _compute_get_name(self):
        for rec in self:
            if rec.stu_name:
                rec.relative_name = rec.stu_name.name
            else:
                rec.relative_name = rec.name

    family_contact_id = fields.Many2one('student.student', 'Referensi Siswa')
    rel_name = fields.Selection([('exist', 'Kaitkan ke Siswa'),
                                 ('new', 'Buat Relasi Baru')],
                                'Relasi ke Siswa', help="Pilih Nama",
                                required=True)
    user_id = fields.Many2one('res.users', 'ID User', ondelete="cascade")
    stu_name = fields.Many2one('student.student', 'Siswa Terdaftar',
                               help="Pilih dari siswa terdaftar")
    name = fields.Char('Nama')
    relation = fields.Many2one('student.relation.master', 'Relasi',
                               required=True)
    phone = fields.Char('Telp', required=True)
    email = fields.Char('E-Mail')
    relative_name = fields.Char(compute='_compute_get_name', string='Nama Relasi')


class StudentRelationMaster(models.Model):
    ''' Student Relation Information '''
    _name = "student.relation.master"
    _description = "Informasi Relasi Siswa"

    name = fields.Char('Nama', required=True, help="Masukan nama relasi")
    seq_no = fields.Integer('Sequence')


class GradeMaster(models.Model):
    _name = 'grade.master'
    _description = "Master Data Nilai"

    name = fields.Char('Nilai', required=True)
    grade_ids = fields.One2many('grade.line', 'grade_id', 'Baris Nilai')


class GradeLine(models.Model):
    _name = 'grade.line'
    _description = "Baris Nilai"
    _rec_name = 'grade'

    from_mark = fields.Integer('Mulai Angka', required=True,
                               help='Nilai akan mulai dari angka ini.')
    to_mark = fields.Integer('Sampai Angka', required=True,
                             help='Nilai akan berakhir diangka ini.')
    grade = fields.Char('Nilai', required=True, help="Nilai")
    sequence = fields.Integer('Sequence', help="Urutan nilai.")
    fail = fields.Boolean('Gagal', help='Jikan kolom gagal dicek,\
                                  akan membuat nilai gagal ketika terpenuhi.')
    grade_id = fields.Many2one("grade.master", 'Referensi Nilai')
    name = fields.Char('Nama')


class StudentNews(models.Model):
    _name = 'student.news'
    _description = 'Berita siswa'
    _rec_name = 'subject'
    _order = 'date asc'

    subject = fields.Char('Judul Berita', required=True,
                          help='Judul dari berita siswa.')
    description = fields.Text('Keterangan', help="Keterangan")
    date = fields.Datetime('Tanggal Jatuh Tempo', help='Tanggal jatuh tempo berita.')
    user_ids = fields.Many2many('res.users', 'user_news_rel', 'id', 'user_ids',
                                'Untuk User',
                                help='User yang menerima berita.')
    color = fields.Integer('Color Index', default=0)

    @api.constrains("date")
    def checknews_dates(self):
        new_date = datetime.now()
        if self.date < new_date:
            raise ValidationError(_('''Configure expiry date greater than
            current date!'''))

    @api.multi
    def news_update(self):
        '''Method to send email to student for news update'''
        emp_obj = self.env['hr.employee']
        obj_mail_server = self.env['ir.mail_server']
        user = self.env['res.users'].browse(self._context.get('uid'))
        # Check if out going mail configured
        mail_server_ids = obj_mail_server.search([])
        if not mail_server_ids:
            raise except_orm(_('Mail Error'),
                             _('''No mail outgoing mail server
                               specified!'''))
        mail_server_record = mail_server_ids[0]
        email_list = []
        # Check email is defined in student
        for news in self:
            if news.user_ids and news.date:
                email_list = [news_user.email for news_user in news.user_ids
                              if news_user.email]
                if not email_list:
                    raise except_orm(_('User Email Error!'),
                                     _("User harus memiliki email !"))
            # Check email is defined in user created from employee
            else:
                for employee in emp_obj.search([]):
                    if employee.work_email:
                        email_list.append(employee.work_email)
                    elif employee.user_id and employee.user_id.email:
                        email_list.append(employee.user_id.email)
                if not email_list:
                    raise except_orm(_('Email Error!'),
                                     _("Belum ada email!"))
            news_date = news.date
            # Add company name while sending email
            company = user.company_id.name or ''
            body = """Bismillah,<br/><br/>
                    Assalamualaykum warohmatullah wabarokatuh, <br/><br/>
                    Ada berita dari sekolah <b>%s</b> dituliskan di %s<br/>
                    <br/> %s <br/><br/>
                    Syukron wa Jazakumullah Khayran.""" % (company,
                                     news_date.strftime('%d-%m-%Y %H:%M:%S'),
                                     news.description or '')
            smtp_user = mail_server_record.smtp_user or False
            # Check if mail of outgoing server configured
            if not smtp_user:
                raise except_orm(_('Email Configuration '),
                                 _("Kindly,Configure Outgoing Mail Server!"))
            notification = 'Notifikasi berita terbaru.'
            # Configure email
            message = obj_mail_server.build_email(email_from=smtp_user,
                                                  email_to=email_list,
                                                  subject=notification,
                                                  body=body,
                                                  body_alternative=body,
                                                  reply_to=smtp_user,
                                                  subtype='html')
            # Send Email configured above with help of send mail method
            obj_mail_server.send_email(message=message,
                                       mail_server_id=mail_server_ids[0].id)
        return True


class StudentReminder(models.Model):
    _name = 'student.reminder'
    _description = "Pengingat Siswa"

    @api.model
    def check_user(self):
        '''Method to get default value of logged in Student'''
        return self.env['student.student'].search([('user_id', '=',
                                                    self._uid)]).id

    stu_id = fields.Many2one('student.student', 'Nama Siswa', required=True,
                             default=check_user)
    name = fields.Char('Judul')
    date = fields.Date('Tanggal')
    description = fields.Text('Keterangan')
    color = fields.Integer('Color Index', default=0)


class StudentCast(models.Model):
    _name = "student.cast"
    _description = "Agama Siswa"

    name = fields.Char("Agama", required=True)


class ClassRoom(models.Model):
    _name = "class.room"
    _description = "Ruang Kelas"

    name = fields.Char("Nama")
    number = fields.Char("Nomor Ruang")


class Report(models.Model):
    _inherit = "ir.actions.report"

    @api.multi
    def render_template(self, template, values=None):
        student_id = self.env['student.student'].\
            browse(self._context.get('student_id', False))
        if student_id and student_id.state == 'draft':
            raise ValidationError(_('''Anda tidak dapat mencetak lapora
                siwa yang belum dikonfirmasi!'''))
        return super(Report, self).render_template(template, values)
