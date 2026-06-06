define(['action-handler'], (Dep) => {

    return class extends Dep {

        initCreateOpportunityFromLead() {}

        isCreateOpportunityFromLeadVisible() {
            const status = this.view.model.get('status');

            return !['Converted', 'Dead', 'Recycled'].includes(status);
        }

        async createOpportunityFromLead() {
            const buttonName = 'createOpportunityFromLead';

            const confirmed = await new Promise(resolve => {
                this.view.confirm({
                    message: 'Creare un\'Opportunità da questo Lead?',
                    confirmText: 'Converti',
                }, () => resolve(true));

                this.view.once('cancel', () => resolve(false));
            });

            if (!confirmed) {
                return;
            }

            this.view.disableMenuItem(buttonName);

            try {
                const attributes = await Espo.Ajax.postRequest('Lead/action/getConvertAttributes', {
                    id: this.view.model.id,
                });

                const response = await Espo.Ajax.postRequest('Lead/action/convert', {
                    id: this.view.model.id,
                    records: {
                        Opportunity: attributes.Opportunity || {},
                    },
                });

                Espo.Ui.success(this.view.translate('Converted', 'labels', 'Lead'));

                await this.view.model.fetch();

                const opportunityId = response?.Opportunity?.id;

                if (opportunityId) {
                    this.view.getRouter().navigate(
                        '#Opportunity/view/' + opportunityId,
                        {trigger: true}
                    );
                }
            } catch (e) {
                Espo.Ui.error(this.view.translate('Error'));
            } finally {
                this.view.enableMenuItem(buttonName);
            }
        }
    };
});
