class ArtistDashboardData:
    def __init__(self, total_sales, this_month_sales, total_commissions, pending_commissions, available_for_payout, referral_links):
        self.total_sales = total_sales
        self.this_month_sales = this_month_sales
        self.total_commissions = total_commissions
        self.pending_commissions = pending_commissions
        self.available_for_payout = available_for_payout
        self.referral_links = referral_links

class AdminDashboardData:
    def __init__(self, total_artists, total_sales, total_commissions_paid, monthly_sales):
        self.total_artists = total_artists
        self.total_sales = total_sales
        self.total_commissions_paid = total_commissions_paid
        self.monthly_sales = monthly_sales