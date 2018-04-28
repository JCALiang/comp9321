class Teacher:
	def __init__(self, name, course, students={}):
		self.name = name
		self.course = course
		self.students = students
	def prints(self):
		print(self.students)

class Student:
	def __init__(self, id, first_name, last_name, gender):
		self.id = id
		self.first_name = first_name
		self.last_name = last_name
		self.gender = gender


