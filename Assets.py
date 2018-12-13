

class Asset:
	def __init__(self, value = 0, owner = None, grow = 0, liquid = False):
		self.value 	= value 
		self.owner 	= owner
		self.grow  	= grow
		self.liquid = liquid # whether funds can be immediately withdrawn 
		
	def appreciate(self, by = None, type = 'percent'):
		if by is None:
			by = self.grow
		if type == 'percent':
			self.value = (1-by)*self.value
		elif type == 'value':
			self.value -= by
			
	def change_ownership(self, owner):
		self.owner.assets = [i for i in self.owner.assets if i != self] # remove asset from list of owner's assets
		self.owner = owner 				# change to new owner
		self.owner.assets.append(self) 	# add to new owner's list of assets
	
	def destroy(self):
		self.owner.assets = [i for i in self.owner.assets if i != self]
	
	def next(self):
		self.appreciate()
		if self.value <= 0:
			self.destroy()
		

class Account:
	def __init__(self, value = 0, owner = None, grow = 0, limit = 0, bank = None):
		Asset.__init__(self, value = value, owner = owner, grow = grow, liquid = True)
		self.limit = limit # withdraw limit for savings accounts
		self.bank = bank
		
		if bank is not None:
			self.bank.liabilities.append(self)
		
	def withdraw(self, x):
		x = abs(x)
		if x > self.limit:
			x = self.limit
		if x > self.value:
			x = self.value 
		self.owner.cash += x
		self.value -= x
		if self.bank is not None:
			self.bank.change_reserves(-x)
		
	def deposit(self, x):
		x = abs(x)
		if x > self.owner.cash:
			x = self.owner.cash
		self.owner.cash -= x
		self.value += x
		if self.bank is not None:
			self.bank.change_reserves(x)
		
	def close(self):
		if self.value >= 0:
			self.owner.cash += self.value 
			self.bank.change_reserves(-self.value)
			self.destroy()
		else:
			abs_value = abs(self.value)
			if self.owner.cash > abs_value:
				self.owner.cash -= abs_value
				self.deposit(abs_value)
				self.destroy()

	def destroy(self):
		self.bank.liabilities = [i for i in self.bank.liabilities if i != self]
		self.owner.assets = [i for i in self.owner.assets if i != self]
		
	
		


		
class Loan(Asset):
	def __init__(self, value = 0, owner = None, borrower = None, length = 1, interest = 0, collateral = None, owner_account = None, borrower_account = None):
		Asset.__init__(self, owner = owner, value = value, liquid = False)
		self.borrower 	= borrower
		self.length 	= length
		self.maturity 	= length
		self.loan_amt 	= value 
		self.interest 	= interest 
		self.collateral = collateral
		self.owner_account 		= owner_account 	# account to receive payment
		self.borrower_account 	= borrower_account 	# account to link to payment
		
		if borrower is not None:
			self.borrower.liabilities.append(self)
		
	def calculate_interest(self):
		return(self.value * self.interest)
		
	def calculate_principal(self):
		return(self.value/self.maturity)
		
	def pay(self, x, principal = True):
		if self.borrower_account is None:
			if self.borrower.cash < x:
				resid = x - self.borrower.cash
				receipt = self.borrower.cash
				self.borrower.cash = 0
					if principal is True:
						self.value -= receipt
						self.default(resid, principal = True)
					else:
						self.default(resid, principal = False)
			else:
				self.borrower.cash -= x
				receipt = x
				if principal is True:
					self.value -= x
		else:
			if self.borrower_account.value < x:
				resid = x - self.borrower_account.value
				receipt = self.borrower_account.value 
				self.borrower_account.value = 0
				if resid > self.borrower.cash:
					receipt += self.borrower.cash
					resid -= self.borrower.cash
					self.borrower.cash = 0
					if principal is True:
						self.value -= receipt
						self.default(resid, principal = True)
					else:
						self.default(resid, principal = False)
				else:
					receipt += resid 
					self.borrower.cash -= resid 
					if principal is True:
						self.value -= receipt
			else:
				self.borrower_account.value -= x
				receipt = x 
				if principal is True:
					self.value -= x
		
		if self.owner_account is None:
			self.owner.cash += receipt
		else:
			self.owner_account.value += receipt
			
	
	def default(self, amount = 0, principal = False):
		# if no amount to pay off is specified, then entire principal is assumed
		if amount == 0:
			amount = self.principal
		
		receipt = 0
		# loop across borrower's liquid assets for additional funds. If have, then use those funds to pay down what is left over
		for i in self.borrower.assets:
			if amount > 0:
				if i.liquid is True:
					if i.value > amount:
						i.value -= amount
						if principal is True:
							self.value -= amount
						receipt += amount 
						amount = 0
					else:
						amount -= i.value 
						receipt += i.value
						if principal is True:
							self.value -= i.value 
						i.value = 0
						
		# if ammount to pay off is still positive, either loan or assets must be transferred
		# First, try to obtain loan
		if amount > 0 and self.borrower_account is not None:
			receive_loan = self.borrower_account.bank.request_loan(self.borrower, amount)
			if receive_loan is True:
				self.borrower_account.bank.lend(self.borrower, amount)
				self.borrower_account -= amount
				if principal is True:
					self.value -= amount  
				amount = 0
		
		# If not successful, look at collateral
		if amount > 0 and self.collateral is not None:
			amount -= self.collateral.value
			if principal is True:
				self.value -= self.collateral.value
			# perhaps give back any excess? 
			self.collateral.change_ownership(owner = self.owner)
			self.borrower.defaults.append(0) # add another default. value is time since last default
			
		if amount > 0:
			self.borrower.bankruptcy()	
		
		if receipt > 0:
			if self.owner_account is None:
				self.owner.cash += receipt
			else:
				self.owner_account.value += receipt
			
	
	def destroy(self):
		self.borrower.liabilities = [i for i in self.borrower.liabilities if i != self]
		self.owner.assets = [i for i in self.owner.assets if i != self]
		
	def next(self):
		principal_payment = self.calculate_principal()
		interest_payment  = self.calculate_interest()
		
		self.pay(interest_payment, principal = False)
		self.pay(principal_payment, principal = True)
		
		if self.value <= 0:
			self.destroy()
		
		self.maturity -= 1
		if self.maturity == 0:
			if self.principal > 0:
				self.pay(self.principal, principal = True)
			self.destroy()




		
			
class EcAgent:
	def __init__(self, cash = 0, assets = [], liabilities = []):
		self.cash = cash
		self.assets = assets
		self.liabilities = liabilities 
		self.defaults = []
	
	def sum_assets(self):
		return(sum([i.value for i in self.assets]))
		
	def sum_liabilities(self):
		return(sum([i.value for i in self.liabilities]))
	
	def equity(self):
		return(self.sum_assets() - self.sum_liabilities())
		
	def leverage(self):
		ass = self.sum_assets()
		lia = self.sum_liabilities()
		eqt = ass - lia
		return(ass/eqt)
		
	def bankruptcy(self):	
	
	def next(self):
		# add one to any time period since default
		self.defaults = [i+1 for i in self.defaults]
		
		# pass next to assets
		for i in self.assets:
			i.next()
			
		
class Bank(EcAgent):
	def __init__(self, cash = 0, reserves = 0, assets = [], liabilities = [], rrequire = 0.1):
		EcAgent.__init__(self, cash = cash, assets = assets, liabilities = liabilities)
		self.reserves = reserves
		self.rrequire = rrequire # reserve requirement
	
	def total_deposits(self):
	
	def excess_reserves(self):
		
	def check_rratio(self):
		
	def change_reserves(self, x):
		
	def lend(self, borrower, amount, interest, length):
		
	def request_loan(self, borrower, amount):

		
	
Bank = Agent(cash = 1000)
Pers = Agent(cash = 1000)
lol = Loan(owner = Bank, borrower = Pers, principal = 500, interest = 0.05, length = 10)
